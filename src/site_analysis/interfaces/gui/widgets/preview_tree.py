"""Preview table widget for validation preview rows."""

import tkinter as tk
from tkinter import ttk


class PreviewTree(tk.Frame):
    """A scrollable treeview for displaying preview data."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._tree = ttk.Treeview(self, show="headings")
        vsb = ttk.Scrollbar(self, orient="vertical", command=self._tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def set_data(self, columns, rows):
        """Populate the treeview with columns and rows."""
        self._tree.delete(*self._tree.get_children())
        self._tree["columns"] = columns
        for col in columns:
            self._tree.heading(col, text=col)
            self._tree.column(col, width=100, anchor="center")
        for row in rows:
            values = [row.get(col, "") for col in columns]
            self._tree.insert("", "end", values=values)

    def clear(self):
        """Clear all data."""
        self._tree.delete(*self._tree.get_children())
        self._tree["columns"] = []
