"""FastAPI HTTP interface for the site-analysis engine."""

import asyncio
import json
import math
import shutil
import tempfile
import threading
import time
import traceback
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from site_analysis.application.analysis_service import SiteAnalysisService
from site_analysis.application.import_service import ImportService
from site_analysis.domain.value_objects import ColumnMapping, ValidationResult
from site_analysis.infrastructure.repositories.excel_result_exporter import ExcelResultExporter
from site_analysis.infrastructure.repositories.repository_factory import RepositoryFactory
from site_analysis.interfaces.gui.view_model import MainViewModel


def _clean_preview_rows(rows: List[Dict]) -> List[Dict]:
    """Convert preview rows into JSON-safe values (NaN→None, Timestamp→str)."""
    cleaned = []
    for row in rows:
        clean: Dict[str, Any] = {}
        for k, v in row.items():
            if isinstance(v, float) and math.isnan(v):
                clean[k] = None
            elif hasattr(v, "isoformat"):
                clean[k] = (
                    v.isoformat()
                    if v is not None and not (isinstance(v, float) and math.isnan(v))
                    else None
                )
            else:
                clean[k] = v
        cleaned.append(clean)
    return cleaned


app = FastAPI(title="Site Analysis API")

# Allow Electron frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session/job storage (safe for single-user desktop usage)
_upload_sessions: Dict[str, dict] = {}
_analysis_jobs: Dict[str, dict] = {}

TEMP_DIR = Path(tempfile.gettempdir()) / "site_analysis_api"
TEMP_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload")
def upload_file(file_type: str = Form(...), file: UploadFile = File(...)):
    """Upload an AOI or Site file; return columns and auto-detected mapping."""
    suffix = Path(file.filename or "data.xlsx").suffix
    session_id = f"{file_type}_{uuid.uuid4().hex}"
    dest = TEMP_DIR / f"{session_id}{suffix}"

    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    vm = MainViewModel()
    if file_type == "aoi":
        vm.load_aoi_file(dest)
        mapping = {
            "scene_col": vm.aoi_mapping.scene_col,
            "boundary_col": vm.aoi_mapping.boundary_col,
        }
        columns = vm.aoi_columns
    elif file_type == "site":
        vm.load_site_file(dest)
        mapping = {
            "name_col": vm.site_mapping.name_col,
            "lon_col": vm.site_mapping.lon_col,
            "lat_col": vm.site_mapping.lat_col,
            "freq_col": vm.site_mapping.freq_col,
            "coverage_type_col": vm.site_mapping.coverage_type_col,
        }
        columns = vm.site_columns
    else:
        return {"error": "file_type must be 'aoi' or 'site'"}

    _upload_sessions[session_id] = {"path": str(dest), "file_type": file_type}

    return {
        "session_id": session_id,
        "file_name": file.filename,
        "columns": columns,
        "mapping": mapping,
    }


class ValidateRequest(BaseModel):
    aoi_session_id: Optional[str] = None
    site_session_id: Optional[str] = None
    scene_col: Optional[str] = None
    boundary_col: Optional[str] = None
    name_col: Optional[str] = None
    lon_col: Optional[str] = None
    lat_col: Optional[str] = None
    freq_col: Optional[str] = None
    coverage_type_col: Optional[str] = None


@app.post("/validate")
def validate(req: ValidateRequest):
    """Validate column mappings against uploaded files."""
    results = []
    importer = ImportService()

    if req.aoi_session_id and req.aoi_session_id in _upload_sessions:
        path = Path(_upload_sessions[req.aoi_session_id]["path"])
        aoi_mapping = ColumnMapping(
            scene_col=req.scene_col or "", boundary_col=req.boundary_col or ""
        )
        result = importer.validate_mapping(path, aoi_mapping, "aoi")
        results.append(result)

    if req.site_session_id and req.site_session_id in _upload_sessions:
        path = Path(_upload_sessions[req.site_session_id]["path"])
        site_mapping = ColumnMapping(
            name_col=req.name_col or "",
            lon_col=req.lon_col or "",
            lat_col=req.lat_col or "",
            freq_col=req.freq_col or "",
            coverage_type_col=req.coverage_type_col or "",
        )
        result = importer.validate_mapping(path, site_mapping, "site")
        results.append(result)

    combined = ValidationResult.combine(results)
    return {
        "valid": combined.is_valid,
        "errors": combined.errors,
        "preview_rows": _clean_preview_rows(combined.preview_rows),
    }


class AnalyzeRequest(BaseModel):
    aoi_session_id: str
    site_session_id: str
    output_path: str
    scene_col: Optional[str] = None
    boundary_col: Optional[str] = None
    name_col: Optional[str] = None
    lon_col: Optional[str] = None
    lat_col: Optional[str] = None
    freq_col: Optional[str] = None
    coverage_type_col: Optional[str] = None


def _run_analysis_job(
    job_id: str,
    aoi_path: Path,
    site_path: Path,
    aoi_mapping: ColumnMapping,
    site_mapping: ColumnMapping,
    output_path: Path,
):
    """Background worker that pushes progress into the job queue."""
    job = _analysis_jobs[job_id]
    queue: asyncio.Queue = job["queue"]

    _last_stage = [5]
    _last_msg = ["准备分析..."]
    _last_detail = [""]
    _stop_heartbeat = threading.Event()

    def push(stage: int, message: str, detail: str = ""):
        _last_stage[0] = stage
        _last_msg[0] = message
        _last_detail[0] = detail
        queue.put_nowait({"stage": stage, "message": message, "detail": detail})

    def heartbeat():
        """Send a heartbeat every second so the UI knows we are alive."""
        while not _stop_heartbeat.wait(timeout=1.0):
            if _analysis_jobs[job_id].get("cancelled"):
                break
            queue.put_nowait(
                {
                    "stage": _last_stage[0],
                    "message": _last_msg[0],
                    "detail": _last_detail[0],
                    "heartbeat": True,
                }
            )

    def _check_cancelled():
        if _analysis_jobs[job_id].get("cancelled"):
            raise RuntimeError("用户取消")

    # Start heartbeat in a daemon thread
    hb_thread = threading.Thread(target=heartbeat, daemon=True)
    hb_thread.start()

    try:
        _check_cancelled()
        push(10, "加载 AOI 数据...", "")
        aoi_repo = RepositoryFactory.create_aoi_repo(aoi_path, aoi_mapping)
        aois = aoi_repo.load_all()

        _check_cancelled()
        push(30, "加载站点数据...", f"AOI 数量: {len(aois)}")
        site_repo = RepositoryFactory.create_site_repo(site_path, site_mapping)
        sites = site_repo.load_all()

        _check_cancelled()
        push(45, "执行 AOI 空间匹配与最近室外站分析...", f"站点数量: {len(sites)}")
        exporter = ExcelResultExporter()
        service = SiteAnalysisService(
            aoi_repo, site_repo, exporter, progress_callback=push
        )
        result = service.run()

        _check_cancelled()
        push(85, "导出结果文件...", f"输出到: {output_path.name}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        exporter.export_with_summary(result.sites, result.summary, output_path)

        push(100, "分析完成", f"结果已保存: {output_path}")
        job["status"] = "success"
        job["output_path"] = str(output_path)
        job["summary"] = {
            "total_sites": result.summary.total_sites,
            "aoi_matched": result.summary.aoi_matched,
            "indoor_sites": result.summary.indoor_sites,
            "outdoor_sites": result.summary.outdoor_sites,
            "indoor_with_outdoor": result.summary.indoor_with_outdoor,
        }
        queue.put_nowait({"done": True})
    except Exception as exc:
        if str(exc) == "用户取消":
            job["status"] = "cancelled"
            job["error"] = "用户取消"
            queue.put_nowait({"cancelled": True})
        else:
            job["status"] = "error"
            job["error"] = str(exc)
            queue.put_nowait({"error": str(exc), "traceback": traceback.format_exc()})
    finally:
        _stop_heartbeat.set()


@app.post("/analyze")
async def analyze(
    background_tasks: BackgroundTasks,
    req: AnalyzeRequest,
):
    """Start an analysis job and return a job ID for progress tracking."""
    if (
        req.aoi_session_id not in _upload_sessions
        or req.site_session_id not in _upload_sessions
    ):
        return {"error": "Invalid session IDs"}

    job_id = uuid.uuid4().hex
    output_path = Path(req.output_path)

    aoi_mapping = ColumnMapping(
        scene_col=req.scene_col or "", boundary_col=req.boundary_col or ""
    )
    site_mapping = ColumnMapping(
        name_col=req.name_col or "",
        lon_col=req.lon_col or "",
        lat_col=req.lat_col or "",
        freq_col=req.freq_col or "",
        coverage_type_col=req.coverage_type_col or "",
    )

    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()
    _analysis_jobs[job_id] = {
        "queue": queue,
        "status": "running",
        "output_path": None,
        "summary": None,
        "error": None,
        "cancelled": False,
    }

    background_tasks.add_task(
        lambda: loop.run_in_executor(
            None,
            _run_analysis_job,
            job_id,
            Path(_upload_sessions[req.aoi_session_id]["path"]),
            Path(_upload_sessions[req.site_session_id]["path"]),
            aoi_mapping,
            site_mapping,
            output_path,
        )
    )

    return {"job_id": job_id}


@app.post("/cancel/{job_id}")
def cancel_job(job_id: str):
    """Signal a running analysis job to stop at the next checkpoint."""
    if job_id not in _analysis_jobs:
        return {"error": "Job not found"}
    _analysis_jobs[job_id]["cancelled"] = True
    return {"cancelled": True}


@app.get("/progress/{job_id}")
async def progress(job_id: str):
    """Stream analysis progress as server-sent events."""
    if job_id not in _analysis_jobs:
        return PlainTextResponse("Job not found", status_code=404)

    job = _analysis_jobs[job_id]
    queue: asyncio.Queue = job["queue"]

    async def event_stream():
        while True:
            try:
                data = await asyncio.wait_for(queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                yield f"event: ping\ndata: {time.time()}\n\n"
                continue

            if data.get("done") or data.get("error") or data.get("cancelled"):
                yield f"event: complete\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                break
            else:
                yield f"event: progress\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.get("/jobs/{job_id}")
def job_status(job_id: str):
    """Get current job status and summary."""
    if job_id not in _analysis_jobs:
        return {"error": "Job not found"}
    job = _analysis_jobs[job_id]
    return {
        "status": job["status"],
        "summary": job.get("summary"),
        "error": job.get("error"),
    }
