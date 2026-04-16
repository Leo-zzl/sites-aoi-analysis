"""GUI entry point for the site analysis tool."""

import tkinter as tk

from site_analysis.interfaces.gui.widgets.main_window import MainWindow


def run_gui():
    """Launch the tkinter application."""
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    run_gui()
