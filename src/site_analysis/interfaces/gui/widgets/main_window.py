"""Main application window — macOS-compatible rendering."""

import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from site_analysis.domain.value_objects import ColumnMapping, ValidationResult
from site_analysis.interfaces.gui.view_model import MainViewModel
from site_analysis.interfaces.gui.widgets.progress_dialog import ProgressDialog


# Colors (buttons and text; frames use system bg on macOS)
RUST = "#C45C26"
DARK_GRAY = "#1F2937"
MID_GRAY = "#6B7280"
LIGHT_GRAY = "#9CA3AF"

FONT_FAMILY = "Microsoft YaHei"


class _FieldRow(tk.Frame):
    """A compact label + combobox row for column mapping."""

    def __init__(self, parent, label_text, combobox_width=18, **kwargs):
        super().__init__(parent, **kwargs)
        self.label = tk.Label(
            self,
            text=label_text,
            fg=MID_GRAY,
            font=(FONT_FAMILY, 10),
        )
        self.label.pack(side=tk.LEFT)

        self.combo = ttk.Combobox(
            self,
            values=[],
            state="readonly",
            width=combobox_width,
        )
        self.combo.pack(side=tk.LEFT, padx=(8, 0))


class MainWindow(tk.Tk):
    """Primary application window."""

    def __init__(self):
        super().__init__()
        self.title("小区-AOI空间匹配与室内站宏站分析工具")
        self.geometry("520x680")
        self.minsize(480, 600)

        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        self.vm = MainViewModel()
        self._result_queue = queue.Queue()
        self._dialog = None

        # Main container
        main = tk.Frame(self, padx=24, pady=24)
        main.pack(fill=tk.BOTH, expand=True)

        # Title
        tk.Label(
            main,
            text="小区-AOI空间匹配分析",
            font=(FONT_FAMILY, 16, "bold"),
            fg=DARK_GRAY,
        ).pack(anchor="w")

        tk.Label(
            main,
            text="上传数据文件，一键完成空间关联分析",
            font=(FONT_FAMILY, 10),
            fg=LIGHT_GRAY,
        ).pack(anchor="w", pady=(2, 16))

        # --- AOI Section ---
        aoi_group = tk.LabelFrame(main, text=" AOI 数据 ", font=(FONT_FAMILY, 10, "bold"), fg=RUST, padx=12, pady=10)
        aoi_group.pack(fill=tk.X, pady=(0, 12))

        aoi_top = tk.Frame(aoi_group)
        aoi_top.pack(fill=tk.X)
        self.aoi_btn = tk.Button(
            aoi_top,
            text="选择文件",
            font=(FONT_FAMILY, 9),
            bg=RUST,
            fg="white",
            activebackground="#A34B1F",
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=self._on_select_aoi,
            padx=12,
            pady=4,
        )
        self.aoi_btn.pack(side=tk.LEFT)
        self.aoi_path_label = tk.Label(aoi_top, text="未选择", fg=LIGHT_GRAY, font=(FONT_FAMILY, 9))
        self.aoi_path_label.pack(side=tk.LEFT, padx=(10, 0))

        aoi_fields = tk.Frame(aoi_group)
        aoi_fields.pack(fill=tk.X, pady=(12, 0))
        self.aoi_scene_row = _FieldRow(aoi_fields, "场景字段")
        self.aoi_scene_row.pack(side=tk.LEFT, padx=(0, 20))
        self.aoi_scene_row.combo.bind("<<ComboboxSelected>>", self._on_aoi_field_changed)

        self.aoi_boundary_row = _FieldRow(aoi_fields, "边界字段")
        self.aoi_boundary_row.pack(side=tk.LEFT)
        self.aoi_boundary_row.combo.bind("<<ComboboxSelected>>", self._on_aoi_field_changed)

        # --- Site Section ---
        site_group = tk.LabelFrame(main, text=" 站点数据 ", font=(FONT_FAMILY, 10, "bold"), fg=RUST, padx=12, pady=10)
        site_group.pack(fill=tk.X, pady=(0, 12))

        site_top = tk.Frame(site_group)
        site_top.pack(fill=tk.X)
        self.site_btn = tk.Button(
            site_top,
            text="选择文件",
            font=(FONT_FAMILY, 9),
            bg=RUST,
            fg="white",
            activebackground="#A34B1F",
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=self._on_select_site,
            padx=12,
            pady=4,
        )
        self.site_btn.pack(side=tk.LEFT)
        self.site_path_label = tk.Label(site_top, text="未选择", fg=LIGHT_GRAY, font=(FONT_FAMILY, 9))
        self.site_path_label.pack(side=tk.LEFT, padx=(10, 0))

        site_fields = tk.Frame(site_group)
        site_fields.pack(fill=tk.X, pady=(10, 0))
        self.site_name_row = _FieldRow(site_fields, "名称")
        self.site_name_row.pack(side=tk.LEFT, padx=(0, 16))
        self.site_name_row.combo.bind("<<ComboboxSelected>>", self._on_site_field_changed)

        self.site_lon_row = _FieldRow(site_fields, "经度")
        self.site_lon_row.pack(side=tk.LEFT)
        self.site_lon_row.combo.bind("<<ComboboxSelected>>", self._on_site_field_changed)

        site_fields2 = tk.Frame(site_group)
        site_fields2.pack(fill=tk.X, pady=(8, 0))
        self.site_lat_row = _FieldRow(site_fields2, "纬度")
        self.site_lat_row.pack(side=tk.LEFT, padx=(0, 16))
        self.site_lat_row.combo.bind("<<ComboboxSelected>>", self._on_site_field_changed)

        self.site_freq_row = _FieldRow(site_fields2, "频段")
        self.site_freq_row.pack(side=tk.LEFT)
        self.site_freq_row.combo.bind("<<ComboboxSelected>>", self._on_site_field_changed)

        site_fields3 = tk.Frame(site_group)
        site_fields3.pack(fill=tk.X, pady=(8, 0))
        self.site_cover_row = _FieldRow(site_fields3, "覆盖类型")
        self.site_cover_row.pack(side=tk.LEFT)
        self.site_cover_row.combo.bind("<<ComboboxSelected>>", self._on_site_field_changed)

        # --- Validate Section ---
        validate_group = tk.LabelFrame(main, text=" 数据校验 ", font=(FONT_FAMILY, 10, "bold"), fg=RUST, padx=12, pady=10)
        validate_group.pack(fill=tk.X, pady=(0, 12))

        val_row = tk.Frame(validate_group)
        val_row.pack(fill=tk.X)
        self.validate_btn = tk.Button(
            val_row,
            text="校验数据",
            font=(FONT_FAMILY, 9, "bold"),
            bg=RUST,
            fg="white",
            activebackground="#A34B1F",
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=self._on_validate,
            padx=14,
            pady=5,
        )
        self.validate_btn.pack(side=tk.LEFT)
        self.result_label = tk.Label(val_row, text="请选择 AOI 文件和站点文件", fg=MID_GRAY, font=(FONT_FAMILY, 9))
        self.result_label.pack(side=tk.LEFT, padx=(12, 0))

        # --- Output Section ---
        out_group = tk.LabelFrame(main, text=" 输出文件 ", font=(FONT_FAMILY, 10, "bold"), fg=RUST, padx=12, pady=10)
        out_group.pack(fill=tk.X, pady=(0, 12))

        out_row = tk.Frame(out_group)
        out_row.pack(fill=tk.X)
        self.output_entry = tk.Entry(out_row, font=(FONT_FAMILY, 9), relief=tk.SUNKEN, bd=1)
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=4)
        default_output = Path.cwd() / f"小区_AOI匹配_1000米限制_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
        self.output_entry.insert(0, str(default_output))

        self.browse_btn = tk.Button(
            out_row,
            text="浏览",
            font=(FONT_FAMILY, 9),
            bg=DARK_GRAY,
            fg="white",
            activebackground="#1F2937",
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=self._on_browse_output,
            padx=12,
            pady=4,
        )
        self.browse_btn.pack(side=tk.RIGHT)

        # --- Analyze Button ---
        self.analyze_btn = tk.Button(
            main,
            text="开始分析",
            font=(FONT_FAMILY, 12, "bold"),
            bg=RUST,
            fg="white",
            activebackground="#A34B1F",
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            state=tk.DISABLED,
            command=self._on_analyze,
            padx=20,
            pady=10,
        )
        self.analyze_btn.pack(fill=tk.X, pady=(4, 0))

        # --- Progress Bar ---
        self.progress_canvas = tk.Canvas(main, height=6, bg="#E5E7EB", highlightthickness=0)
        self.progress_canvas.pack(fill=tk.X, pady=(16, 0))
        self._draw_progress(0)

    def _draw_progress(self, percent: int):
        self.progress_canvas.delete("all")
        width = self.progress_canvas.winfo_width() or 200
        filled = int(width * percent / 100)
        self.progress_canvas.create_rectangle(0, 0, filled, 6, fill=RUST, outline="")
        self.progress_canvas.create_rectangle(filled, 0, width, 6, fill="#E5E7EB", outline="")

    def _on_select_aoi(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="选择 AOI 文件",
            filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv"), ("所有文件", "*.*")],
        )
        if path:
            p = Path(path)
            self.vm.load_aoi_file(p)
            self.aoi_path_label.config(text=str(p.name), fg=DARK_GRAY)
            self._update_aoi_combos()
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
            self.site_path_label.config(text=str(p.name), fg=DARK_GRAY)
            self._update_site_combos()
            self._reset_analysis_state()

    def _update_aoi_combos(self):
        columns = [""] + self.vm.aoi_columns
        self.aoi_scene_row.combo.config(values=columns)
        self.aoi_boundary_row.combo.config(values=columns)
        self.aoi_scene_row.combo.set(self.vm.aoi_mapping.scene_col)
        self.aoi_boundary_row.combo.set(self.vm.aoi_mapping.boundary_col)

    def _update_site_combos(self):
        columns = [""] + self.vm.site_columns
        self.site_name_row.combo.config(values=columns)
        self.site_lon_row.combo.config(values=columns)
        self.site_lat_row.combo.config(values=columns)
        self.site_freq_row.combo.config(values=columns)
        self.site_cover_row.combo.config(values=columns)
        self.site_name_row.combo.set(self.vm.site_mapping.name_col)
        self.site_lon_row.combo.set(self.vm.site_mapping.lon_col)
        self.site_lat_row.combo.set(self.vm.site_mapping.lat_col)
        self.site_freq_row.combo.set(self.vm.site_mapping.freq_col)
        self.site_cover_row.combo.set(self.vm.site_mapping.coverage_type_col)

    def _on_aoi_field_changed(self, _event=None):
        mapping = ColumnMapping(
            scene_col=self.aoi_scene_row.combo.get(),
            boundary_col=self.aoi_boundary_row.combo.get(),
        )
        self.vm.set_aoi_mapping(mapping)
        self._reset_analysis_state()

    def _on_site_field_changed(self, _event=None):
        mapping = ColumnMapping(
            name_col=self.site_name_row.combo.get(),
            lon_col=self.site_lon_row.combo.get(),
            lat_col=self.site_lat_row.combo.get(),
            freq_col=self.site_freq_row.combo.get(),
            coverage_type_col=self.site_cover_row.combo.get(),
        )
        self.vm.set_site_mapping(mapping)
        self._reset_analysis_state()

    def _reset_analysis_state(self):
        self.analyze_btn.config(state=tk.DISABLED)
        self.result_label.config(text="请先点击【校验数据】检查文件格式", fg=MID_GRAY)
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
                self.result_label.config(text="校验通过，可以点击【开始分析】", fg="#16A34A")
                self.analyze_btn.config(state=tk.NORMAL)
            else:
                self.result_label.config(text="校验失败，请检查字段映射与数据格式", fg=RUST)
                self.analyze_btn.config(state=tk.DISABLED)
                messagebox.showerror(parent=self, title="校验失败", message="\n".join(result.errors))
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
                # Delay messagebox on macOS to avoid grab/focus deadlock
                self.after(50, lambda msg=item[1]: messagebox.showerror(parent=self, title="分析失败", message=msg))
                return
            elif item[0] == "success":
                dialog.close()
                self.analyze_btn.config(state=tk.NORMAL, text="开始分析")
                self._draw_progress(100)
                summary = getattr(self.vm.analysis_result, "summary", None)
                if summary:
                    text = (
                        f"分析完成！结果已保存至 {item[1]}\n"
                        f"总站点数：{summary.total_sites}  |  "
                        f"AOI已匹配：{summary.aoi_matched}  |  "
                        f"室内站：{summary.indoor_sites}  |  "
                        f"室外站：{summary.outdoor_sites}  |  "
                        f"1000米内找到室外站：{summary.indoor_with_outdoor}"
                    )
                else:
                    text = f"分析完成！结果已保存至 {item[1]}"
                self.result_label.config(text=text, fg="#16A34A")
                return

        if not updated:
            self.after(100, self._check_analysis_result, dialog)
