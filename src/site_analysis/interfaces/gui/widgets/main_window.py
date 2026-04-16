"""Main application window."""

import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from site_analysis.domain.value_objects import ColumnMapping, ValidationResult
from site_analysis.interfaces.gui.view_model import MainViewModel
from site_analysis.interfaces.gui.widgets.mapping_frame import MappingFrame
from site_analysis.interfaces.gui.widgets.preview_tree import PreviewTree
from site_analysis.interfaces.gui.widgets.progress_dialog import ProgressDialog


class MainWindow(tk.Tk):
    """Primary application window."""

    def __init__(self):
        super().__init__()
        self.title("小区-AOI空间匹配与室内站宏站分析工具")
        self.geometry("720x680")
        self.minsize(680, 600)
        self.resizable(True, True)

        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        self.vm = MainViewModel()
        self._result_queue = queue.Queue()
        self._dialog = None

        # Main container
        main = tk.Frame(self, padx=16, pady=16)
        main.pack(fill=tk.BOTH, expand=True)

        # Title
        tk.Label(
            main,
            text="小区-AOI空间匹配与室内站宏站分析",
            font=("Microsoft YaHei", 16, "bold"),
        ).pack(pady=(0, 12))

        # --- AOI Section ---
        aoi_group = tk.LabelFrame(main, text="AOI 数据", font=("Microsoft YaHei", 10, "bold"), padx=10, pady=8)
        aoi_group.pack(fill=tk.X, pady=4)

        aoi_top = tk.Frame(aoi_group)
        aoi_top.pack(fill=tk.X)
        tk.Button(
            aoi_top,
            text="选择文件",
            font=("Microsoft YaHei", 9),
            width=10,
            command=self._on_select_aoi,
        ).pack(side=tk.LEFT)
        self.aoi_path_label = tk.Label(aoi_top, text="未选择", fg="gray", font=("Microsoft YaHei", 9))
        self.aoi_path_label.pack(side=tk.LEFT, padx=(8, 0))

        self.aoi_status = tk.Label(aoi_group, text="", font=("Microsoft YaHei", 9))
        self.aoi_status.pack(anchor=tk.W, pady=(4, 0))

        self.aoi_mapping = MappingFrame(
            aoi_group,
            fields=[
                ("场景名", "scene_col"),
                ("边界 (WKT)", "boundary_col"),
            ],
            on_change=self._on_aoi_mapping_changed,
        )
        self.aoi_mapping.pack(fill=tk.X, pady=(4, 0))

        # --- Site Section ---
        site_group = tk.LabelFrame(main, text="站点数据", font=("Microsoft YaHei", 10, "bold"), padx=10, pady=8)
        site_group.pack(fill=tk.X, pady=4)

        site_top = tk.Frame(site_group)
        site_top.pack(fill=tk.X)
        tk.Button(
            site_top,
            text="选择文件",
            font=("Microsoft YaHei", 9),
            width=10,
            command=self._on_select_site,
        ).pack(side=tk.LEFT)
        self.site_path_label = tk.Label(site_top, text="未选择", fg="gray", font=("Microsoft YaHei", 9))
        self.site_path_label.pack(side=tk.LEFT, padx=(8, 0))

        self.site_status = tk.Label(site_group, text="", font=("Microsoft YaHei", 9))
        self.site_status.pack(anchor=tk.W, pady=(4, 0))

        self.site_mapping = MappingFrame(
            site_group,
            fields=[
                ("站点名称", "name_col"),
                ("经度", "lon_col"),
                ("纬度", "lat_col"),
                ("频段", "freq_col"),
                ("覆盖类型", "coverage_type_col"),
            ],
            on_change=self._on_site_mapping_changed,
        )
        self.site_mapping.pack(fill=tk.X, pady=(4, 0))

        # --- Validation Button ---
        self.validate_btn = tk.Button(
            main,
            text="校验数据",
            font=("Microsoft YaHei", 10, "bold"),
            bg="#2196F3",
            fg="white",
            activebackground="#1976D2",
            activeforeground="white",
            width=14,
            command=self._on_validate,
        )
        self.validate_btn.pack(pady=10)

        self.result_label = tk.Label(main, text="请选择 AOI 文件和站点文件", font=("Microsoft YaHei", 10), fg="#666")
        self.result_label.pack()

        # --- Output Path ---
        out_group = tk.LabelFrame(main, text="输出文件", font=("Microsoft YaHei", 10, "bold"), padx=10, pady=6)
        out_group.pack(fill=tk.X, pady=6)
        out_row = tk.Frame(out_group)
        out_row.pack(fill=tk.X)
        self.output_entry = tk.Entry(out_row, font=("Microsoft YaHei", 9))
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        default_output = Path.cwd() / f"小区_AOI匹配_1000米限制_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
        self.output_entry.insert(0, str(default_output))
        tk.Button(
            out_row,
            text="浏览",
            font=("Microsoft YaHei", 9),
            width=8,
            command=self._on_browse_output,
        ).pack(side=tk.RIGHT)

        # --- Analyze Button ---
        self.analyze_btn = tk.Button(
            main,
            text="开始分析",
            font=("Microsoft YaHei", 11, "bold"),
            bg="#4CAF50",
            fg="white",
            activebackground="#388E3C",
            activeforeground="white",
            width=16,
            height=1,
            state=tk.DISABLED,
            command=self._on_analyze,
        )
        self.analyze_btn.pack(pady=8)

        # --- Progress Bar in Main Window ---
        self.progress_frame = tk.Frame(main)
        self.progress_frame.pack(fill=tk.X, pady=4)
        self.progress_bar = tk.Canvas(self.progress_frame, height=8, bg="#e0e0e0", highlightthickness=0)
        self.progress_bar.pack(fill=tk.X)
        self._draw_progress(0)

        # --- Preview ---
        preview_group = tk.LabelFrame(main, text="数据预览", font=("Microsoft YaHei", 10, "bold"), padx=6, pady=6)
        preview_group.pack(fill=tk.BOTH, expand=True, pady=4)
        self.preview_tree = PreviewTree(preview_group)
        self.preview_tree.pack(fill=tk.BOTH, expand=True)

        # --- Summary ---
        summary_group = tk.LabelFrame(main, text="分析摘要", font=("Microsoft YaHei", 10, "bold"), padx=6, pady=6)
        summary_group.pack(fill=tk.X, pady=4)
        self.summary_text = tk.Text(
            summary_group,
            height=5,
            state=tk.DISABLED,
            wrap=tk.WORD,
            bg="#f7f7f7",
            fg="#333333",
            font=("Microsoft YaHei", 10),
            relief=tk.FLAT,
        )
        self.summary_text.pack(fill=tk.BOTH, expand=True)

    def _draw_progress(self, percent: int):
        self.progress_bar.delete("all")
        width = self.progress_bar.winfo_width() or 200
        filled = int(width * percent / 100)
        self.progress_bar.create_rectangle(0, 0, filled, 8, fill="#4CAF50", outline="")
        self.progress_bar.create_rectangle(filled, 0, width, 8, fill="#e0e0e0", outline="")

    def _update_mapping_status(self, mapping: ColumnMapping, label: tk.Label, kind: str):
        missing = mapping.missing_aoi_fields() if kind == "aoi" else mapping.missing_site_fields()
        if not missing:
            label.config(text="✅ 字段已自动识别，可手动修改", fg="green")
        else:
            names = {
                "scene_col": "场景名", "boundary_col": "边界",
                "name_col": "站点名称", "lon_col": "经度", "lat_col": "纬度",
                "freq_col": "频段", "coverage_type_col": "覆盖类型",
            }
            label.config(text=f"⚠️ 未识别字段: {', '.join(names.get(m, m) for m in missing)}，请手动选择", fg="orange")

    def _on_select_aoi(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="选择 AOI 文件",
            filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv"), ("所有文件", "*.*")],
        )
        if path:
            p = Path(path)
            self.vm.load_aoi_file(p)
            self.aoi_path_label.config(text=str(p), fg="black")
            self.aoi_mapping.set_columns(self.vm.aoi_columns)
            self.aoi_mapping.set_mapping(self.vm.aoi_mapping)
            self._update_mapping_status(self.vm.aoi_mapping, self.aoi_status, "aoi")
            self._reset_analysis_state()

    def _on_select_site(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="选择站点文件",
            filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv"), ("所有文件", "*.*")],
        )
        if path:
            p = Path(path)
            self.vm.load_site_file(p)
            self.site_path_label.config(text=str(p), fg="black")
            self.site_mapping.set_columns(self.vm.site_columns)
            self.site_mapping.set_mapping(self.vm.site_mapping)
            self._update_mapping_status(self.vm.site_mapping, self.site_status, "site")
            self._reset_analysis_state()

    def _on_aoi_mapping_changed(self, mapping: ColumnMapping):
        self.vm.set_aoi_mapping(mapping)
        self._update_mapping_status(mapping, self.aoi_status, "aoi")
        self._reset_analysis_state()

    def _on_site_mapping_changed(self, mapping: ColumnMapping):
        self.vm.set_site_mapping(mapping)
        self._update_mapping_status(mapping, self.site_status, "site")
        self._reset_analysis_state()

    def _reset_analysis_state(self):
        self.analyze_btn.config(state=tk.DISABLED)
        self.result_label.config(text="请先点击【校验数据】检查文件格式", fg="#666")
        self.preview_tree.clear()
        self._set_summary_text("")
        self._draw_progress(0)

    def _on_browse_output(self):
        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".xlsx",
            filetypes=[("Excel 文件", "*.xlsx")],
            title="保存分析结果",
            initialfile=Path(self.output_entry.get()).name,
        )
        if path:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, path)

    def _on_validate(self):
        try:
            if not self.vm.aoi_file_path or not self.vm.site_file_path:
                messagebox.showwarning(parent=self, title="提示", message="请先选择 AOI 文件和站点文件")
                return

            self.result_label.config(text="正在校验数据格式与字段映射...", fg="#1976D2")
            self.update_idletasks()

            result: ValidationResult = self.vm.validate()
            if result.is_valid:
                self.result_label.config(text="✅ 校验通过，可以点击【开始分析】", fg="green")
                self.analyze_btn.config(state=tk.NORMAL)
            else:
                self.result_label.config(text="❌ 校验失败，请检查字段映射与数据格式", fg="red")
                self.analyze_btn.config(state=tk.DISABLED)
                messagebox.showerror(parent=self, title="校验失败", message="\n".join(result.errors))

            if result.preview_rows:
                columns = list(result.preview_rows[0].keys())
                self.preview_tree.set_data(columns, result.preview_rows)
            else:
                self.preview_tree.clear()
        except Exception as exc:
            messagebox.showerror(parent=self, title="校验异常", message=str(exc))

    def _on_analyze(self):
        output_path = Path(self.output_entry.get().strip())
        if not output_path.name:
            messagebox.showwarning(parent=self, title="提示", message="请先设置输出文件路径")
            return

        self.analyze_btn.config(state=tk.DISABLED, text="分析中...")
        self._draw_progress(5)
        self.update_idletasks()

        dialog = ProgressDialog(self)
        self._dialog = dialog

        def worker():
            try:
                self._result_queue.put(("stage", 10, "加载 AOI 数据...", ""))
                self.vm.aoi_repo = self.vm._repository_factory.create_aoi_repo(
                    self.vm.aoi_file_path, self.vm.aoi_mapping
                )
                aois = self.vm.aoi_repo.load_all()
                self._result_queue.put(("stage", 30, "加载站点数据...", f"AOI 数量: {len(aois)}"))
                self.vm.site_repo = self.vm._repository_factory.create_site_repo(
                    self.vm.site_file_path, self.vm.site_mapping
                )
                sites = self.vm.site_repo.load_all()
                self._result_queue.put(("stage", 50, "执行 AOI 空间匹配与最近室外站分析...", f"站点数量: {len(sites)}"))

                from site_analysis.application.analysis_service import SiteAnalysisService
                from site_analysis.infrastructure.repositories.excel_result_exporter import ExcelResultExporter

                service = SiteAnalysisService(self.vm.aoi_repo, self.vm.site_repo, ExcelResultExporter())
                self.vm.analysis_result = service.run()

                self._result_queue.put(("stage", 80, "导出结果文件...", ""))
                self.vm.export_results(output_path)
                self._result_queue.put(("success", output_path))
            except Exception as exc:
                self._result_queue.put(("error", str(exc)))

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        self.after(100, self._check_analysis_result, dialog)

    def _check_analysis_result(self, dialog: ProgressDialog):
        updated = False
        while True:
            try:
                item = self._result_queue.get_nowait()
            except queue.Empty:
                break
            updated = True
            if item[0] == "stage":
                _, percent, text, detail = item
                dialog.set_stage(percent, text, detail)
                self._draw_progress(percent)
            elif item[0] == "error":
                dialog.close()
                self.analyze_btn.config(state=tk.NORMAL, text="开始分析")
                self._draw_progress(0)
                messagebox.showerror(parent=self, title="分析失败", message=item[1])
                return
            elif item[0] == "success":
                dialog.close()
                self.analyze_btn.config(state=tk.NORMAL, text="开始分析")
                self._draw_progress(100)
                summary = self.vm.analysis_result.summary
                text = (
                    f"分析完成！结果已保存。\n"
                    f"总站点数：{summary.total_sites}  |  "
                    f"AOI已匹配：{summary.aoi_matched}  |  "
                    f"室内站：{summary.indoor_sites}  |  "
                    f"室外站：{summary.outdoor_sites}  |  "
                    f"1000米内找到室外站：{summary.indoor_with_outdoor}"
                )
                self._set_summary_text(text)
                messagebox.showinfo(parent=self, title="完成", message=f"结果已保存至：{item[1]}")
                return

        if not updated:
            self.after(100, self._check_analysis_result, dialog)

    def _set_summary_text(self, text: str):
        self.summary_text.config(state=tk.NORMAL)
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert(tk.END, text)
        self.summary_text.config(state=tk.DISABLED)
