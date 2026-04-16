"""Unit tests for MappingFrame widget."""

import tkinter as tk

import pytest

from site_analysis.domain.value_objects import ColumnMapping
from site_analysis.interfaces.gui.widgets.mapping_frame import MappingFrame


class TestMappingFrame:
    """Test field mapping combobox widget."""

    @pytest.fixture
    def root(self):
        root = tk.Tk()
        yield root
        root.destroy()

    @pytest.fixture
    def mapping_frame(self, root):
        changes = []

        def on_change(mapping):
            changes.append(mapping)

        frame = MappingFrame(
            root,
            fields=[
                ("场景名", "scene_col"),
                ("边界", "boundary_col"),
            ],
            on_change=on_change,
        )
        frame.pack()
        frame._test_changes = changes
        return frame

    def test_set_columns_updates_combobox_values(self, mapping_frame):
        mapping_frame.set_columns(["场景", "边界WKT", "备注"])

        combos = mapping_frame._combos
        assert set(combos["scene_col"]["values"]) == {"", "场景", "边界WKT", "备注"}
        assert set(combos["boundary_col"]["values"]) == {"", "场景", "边界WKT", "备注"}

    def test_set_mapping_selects_correct_values(self, mapping_frame):
        mapping_frame.set_columns(["场景", "边界WKT", "备注"])
        mapping_frame.set_mapping(ColumnMapping(scene_col="场景", boundary_col="边界WKT"))

        assert mapping_frame._combos["scene_col"].get() == "场景"
        assert mapping_frame._combos["boundary_col"].get() == "边界WKT"

    def test_set_mapping_with_unknown_value_clears_selection(self, mapping_frame):
        mapping_frame.set_columns(["场景", "边界WKT"])
        mapping_frame.set_mapping(ColumnMapping(scene_col="不存在的列", boundary_col="边界WKT"))

        assert mapping_frame._combos["scene_col"].get() == ""
        assert mapping_frame._combos["boundary_col"].get() == "边界WKT"

    def test_get_mapping_returns_current_selection(self, mapping_frame):
        mapping_frame.set_columns(["场景", "边界WKT", "备注"])
        mapping_frame.set_mapping(ColumnMapping(scene_col="场景", boundary_col="边界WKT"))

        result = mapping_frame.get_mapping()
        assert result.scene_col == "场景"
        assert result.boundary_col == "边界WKT"

    def test_on_change_called_when_user_selects(self, mapping_frame):
        mapping_frame.set_columns(["场景", "边界WKT", "备注"])
        mapping_frame._combos["scene_col"].set("场景")
        mapping_frame._emit_change()

        assert len(mapping_frame._test_changes) == 1
        assert mapping_frame._test_changes[0].scene_col == "场景"

    def test_empty_mapping_when_nothing_selected(self, mapping_frame):
        mapping_frame.set_columns(["场景", "边界WKT"])
        result = mapping_frame.get_mapping()
        assert result.scene_col == ""
        assert result.boundary_col == ""
