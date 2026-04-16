"""Progress dialog showing analysis stages."""

import tkinter as tk
from tkinter import ttk


class ProgressDialog(tk.Toplevel):
    """Modal progress dialog with stage labels."""

    def __init__(self, parent, title="请稍候"):
        super().__init__(parent)
        self.title(title)
        self.geometry("360x160")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._noop)

        self.stage_label = tk.Label(self, text="准备分析...", font=("Microsoft YaHei", 11))
        self.stage_label.pack(pady=(15, 8))

        self.detail_label = tk.Label(self, text="", font=("Microsoft YaHei", 9), fg="gray")
        self.detail_label.pack(pady=(0, 8))

        self.progress = ttk.Progressbar(self, mode="determinate", length=300)
        self.progress.pack(pady=5)
        self.progress["maximum"] = 100
        self.progress["value"] = 0

        self.update_idletasks()
        self._center_over_parent(parent)

    def _noop(self):
        pass

    def _center_over_parent(self, parent):
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def set_stage(self, percent: int, text: str, detail: str = ""):
        self.progress["value"] = percent
        self.stage_label.config(text=text)
        if detail:
            self.detail_label.config(text=detail)
        self.update_idletasks()

    def close(self):
        self.grab_release()
        self.destroy()
