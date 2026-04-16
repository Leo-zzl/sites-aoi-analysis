"""Helper script run by test_gui_launch in a subprocess."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from site_analysis.interfaces.gui.widgets.main_window import MainWindow
import tkinter as tk
from tkinter import ttk
from site_analysis.interfaces.gui.widgets.preview_tree import PreviewTree
from site_analysis.interfaces.gui.widgets.mapping_frame import MappingFrame

win = MainWindow()
win.withdraw()

combos = []
previews = []
mappings = []

def walk(w):
    for c in w.winfo_children():
        if isinstance(c, ttk.Combobox):
            combos.append(str(c))
        if isinstance(c, PreviewTree):
            previews.append(str(c))
        if isinstance(c, MappingFrame):
            mappings.append(str(c))
        walk(c)

walk(win)

print(f"COMBOBOX_COUNT: {len(combos)}")
print(f"PREVIEW_COUNT: {len(previews)}")
print(f"MAPPING_COUNT: {len(mappings)}")
print(f"NEW_UI: {len(combos) == 7 and not previews and not mappings}")

win.destroy()
