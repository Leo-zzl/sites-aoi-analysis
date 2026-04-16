"""Field mapping configuration frame."""

import tkinter as tk
from tkinter import ttk
from typing import Callable, List

from site_analysis.domain.value_objects import ColumnMapping


class MappingFrame(tk.Frame):
    """A frame containing labels and comboboxes for column mapping."""

    def __init__(
        self,
        parent,
        fields: List[tuple],
        on_change: Callable[[ColumnMapping], None] = None,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self._on_change = on_change
        self._combos = {}
        self._columns = []

        for idx, (label_text, attr_name) in enumerate(fields):
            tk.Label(self, text=label_text, font=("Microsoft YaHei", 10)).grid(
                row=idx, column=0, sticky="e", padx=5, pady=3
            )
            combo = ttk.Combobox(self, values=[], state="readonly", width=28)
            combo.grid(row=idx, column=1, sticky="w", padx=5, pady=3)
            combo.bind("<<ComboboxSelected>>", self._emit_change)
            self._combos[attr_name] = combo

    def set_columns(self, columns: List[str]) -> None:
        """Update the combobox values."""
        self._columns = list(columns)
        for combo in self._combos.values():
            combo.configure(values=[""] + self._columns)

    def set_mapping(self, mapping: ColumnMapping) -> None:
        """Set combobox selections from a ColumnMapping."""
        for attr_name, combo in self._combos.items():
            value = getattr(mapping, attr_name, "")
            combo.set(value if value in self._columns else "")

    def get_mapping(self) -> ColumnMapping:
        """Build a ColumnMapping from current combobox selections."""
        kwargs = {attr: combo.get() for attr, combo in self._combos.items()}
        return ColumnMapping(**kwargs)

    def _emit_change(self, _event=None) -> None:
        if self._on_change:
            self._on_change(self.get_mapping())
