"""Unit tests for ValidationResult value object."""

import pytest


class TestValidationResult:
    """Test data validation result logic."""

    def test_success(self):
        from site_analysis.domain.value_objects import ValidationResult

        result = ValidationResult.success(preview_rows=[{"a": 1}])
        assert result.is_valid is True
        assert result.errors == []
        assert result.preview_rows == [{"a": 1}]

    def test_failure(self):
        from site_analysis.domain.value_objects import ValidationResult

        result = ValidationResult.failure(["缺少经度列", "WKT格式错误"])
        assert result.is_valid is False
        assert result.errors == ["缺少经度列", "WKT格式错误"]
        assert result.preview_rows == []

    def test_combine_all_valid(self):
        from site_analysis.domain.value_objects import ValidationResult

        r1 = ValidationResult.success()
        r2 = ValidationResult.success()
        combined = ValidationResult.combine([r1, r2])
        assert combined.is_valid is True

    def test_combine_one_invalid(self):
        from site_analysis.domain.value_objects import ValidationResult

        r1 = ValidationResult.success()
        r2 = ValidationResult.failure(["错误1"])
        combined = ValidationResult.combine([r1, r2])
        assert combined.is_valid is False
        assert "错误1" in combined.errors
