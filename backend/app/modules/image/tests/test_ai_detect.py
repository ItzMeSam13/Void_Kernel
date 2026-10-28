"""
Unit tests for the Smaug AI-generated image detection component.

All model loading and inference is mocked — these tests never download weights.
To run a real-model smoke test, use ``run_smaug.py`` instead.

Run with::

    pytest backend/app/modules/image/tests/test_ai_detect.py -v

Or from inside the Docker container::

    pytest app/modules/image/tests/test_ai_detect.py -v
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from app.modules.image.contracts import (
    SmaugDetectionInput,
    SmaugDetectionOutput,
    ProcessingStatus,
)
from app.modules.image import ai_detect


# ── Helpers ──────────────────────────────────────────────────────────────────

def _create_test_image(path: Path, size: tuple[int, int] = (64, 64)) -> Path:
    """Write a small valid PNG to *path*."""
    img = Image.new("RGB", size, color=(128, 200, 50))
    img.save(path)
    return path


def _create_corrupted_file(path: Path) -> Path:
    """Write random bytes that are not a valid image."""
    path.write_bytes(os.urandom(256))
    return path


# ── Reset singleton between tests ───────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_singleton():
    """Clear the module-level singleton so each test starts clean."""
    ai_detect._detector = None
    ai_detect._model_revision = None
    yield
    ai_detect._detector = None
    ai_detect._model_revision = None


@pytest.fixture()
def mock_smaug():
    """Patch ``_load_detector`` to return a mocked Smaug detector.

    The mocked detector is callable and returns a fixed probability score of
    0.82, simulating a plausible AI-generated image detection result.
    """
    mock_detector = MagicMock()
    mock_detector.return_value = 0.82   # callable: detector(path) -> float
    mock_detector.__call__ = MagicMock(return_value=0.82)

    with patch.object(
        ai_detect,
        "_load_detector",
        return_value=(mock_detector, "smaug_test_rev"),
    ):
        yield mock_detector


@pytest.fixture()
def mock_smaug_low():
    """Mocked detector returning a low probability (0.23) — below default threshold."""
    mock_detector = MagicMock(return_value=0.23)
    with patch.object(
        ai_detect,
        "_load_detector",
        return_value=(mock_detector, "smaug_test_rev"),
    ):
        yield mock_detector


# ── Tests — valid inputs ─────────────────────────────────────────────────────

class TestSmaugValidInputs:
    """Tests with valid image input and successful mocked inference."""

    def test_returns_success(self, tmp_path: Path, mock_smaug):
        img_path = _create_test_image(tmp_path / "test.png")
        inp = SmaugDetectionInput(image_path=str(img_path))
        out = ai_detect.run(inp)

        assert isinstance(out, SmaugDetectionOutput)
        assert out.status == ProcessingStatus.SUCCESS

    def test_ai_probability_is_finite_float(self, tmp_path: Path, mock_smaug):
        img_path = _create_test_image(tmp_path / "test.png")
        inp = SmaugDetectionInput(image_path=str(img_path))
        out = ai_detect.run(inp)

        assert out.ai_probability is not None
        assert isinstance(out.ai_probability, float)
        assert math.isfinite(out.ai_probability)

    def test_ai_probability_in_valid_range(self, tmp_path: Path, mock_smaug):
        img_path = _create_test_image(tmp_path / "test.png")
        inp = SmaugDetectionInput(image_path=str(img_path))
        out = ai_detect.run(inp)

        assert 0.0 <= out.ai_probability <= 1.0

    def test_output_contract_fields(self, tmp_path: Path, mock_smaug):
        img_path = _create_test_image(tmp_path / "test.png")
        inp = SmaugDetectionInput(image_path=str(img_path))
        out = ai_detect.run(inp)

        assert out.model_id == "abacusai/Smaug-AI-Image-Detector"
        assert out.model_revision == "smaug_test_rev"
        assert out.error_message is None
        assert out.detection_threshold == 0.5  # default

    def test_high_score_produces_ai_generated_label(self, tmp_path: Path, mock_smaug):
        """Score 0.82 >= default threshold 0.5 → 'likely_ai_generated'."""
        img_path = _create_test_image(tmp_path / "test.png")
        inp = SmaugDetectionInput(image_path=str(img_path))
        out = ai_detect.run(inp)

        assert out.label == "likely_ai_generated"

    def test_low_score_produces_not_flagged_label(self, tmp_path: Path, mock_smaug_low):
        """Score 0.23 < default threshold 0.5 → 'not_flagged_as_ai_generated'."""
        img_path = _create_test_image(tmp_path / "test.png")
        inp = SmaugDetectionInput(image_path=str(img_path))
        out = ai_detect.run(inp)

        assert out.label == "not_flagged_as_ai_generated"


# ── Tests — configurable threshold ──────────────────────────────────────────

class TestSmaugThreshold:
    """Tests for configurable detection threshold behaviour."""

    def test_custom_threshold_flips_label(self, tmp_path: Path, mock_smaug):
        """Score 0.82 < threshold 0.90 → 'not_flagged_as_ai_generated'."""
        img_path = _create_test_image(tmp_path / "test.png")
        inp = SmaugDetectionInput(image_path=str(img_path), detection_threshold=0.90)
        out = ai_detect.run(inp)

        assert out.label == "not_flagged_as_ai_generated"
        assert out.detection_threshold == 0.90

    def test_threshold_stored_in_output(self, tmp_path: Path, mock_smaug):
        img_path = _create_test_image(tmp_path / "test.png")
        inp = SmaugDetectionInput(image_path=str(img_path), detection_threshold=0.75)
        out = ai_detect.run(inp)

        assert out.detection_threshold == 0.75

    def test_threshold_at_exact_score_boundary(self, tmp_path: Path, mock_smaug):
        """Score 0.82, threshold 0.82 → 'likely_ai_generated' (>= boundary)."""
        img_path = _create_test_image(tmp_path / "test.png")
        inp = SmaugDetectionInput(image_path=str(img_path), detection_threshold=0.82)
        out = ai_detect.run(inp)

        assert out.label == "likely_ai_generated"

    def test_threshold_bounds_validation(self):
        """Pydantic must reject thresholds outside [0, 1]."""
        with pytest.raises(Exception):
            SmaugDetectionInput(image_path="/some/path.png", detection_threshold=1.5)
        with pytest.raises(Exception):
            SmaugDetectionInput(image_path="/some/path.png", detection_threshold=-0.1)


# ── Tests — invalid image ────────────────────────────────────────────────────

class TestSmaugInvalidImage:
    """Tests with missing / invalid / corrupted image files."""

    def test_missing_image_returns_error(self, mock_smaug):
        inp = SmaugDetectionInput(image_path="/nonexistent/path/image.png")
        out = ai_detect.run(inp)

        assert out.status == ProcessingStatus.ERROR
        assert out.ai_probability is None
        assert "does not exist" in out.error_message.lower()

    def test_directory_instead_of_file_returns_error(self, tmp_path: Path, mock_smaug):
        inp = SmaugDetectionInput(image_path=str(tmp_path))
        out = ai_detect.run(inp)

        assert out.status == ProcessingStatus.ERROR
        assert "directory" in out.error_message.lower()

    def test_corrupted_image_returns_error(self, tmp_path: Path, mock_smaug):
        bad_path = _create_corrupted_file(tmp_path / "corrupted.png")
        inp = SmaugDetectionInput(image_path=str(bad_path))
        out = ai_detect.run(inp)

        assert out.status == ProcessingStatus.ERROR
        assert out.ai_probability is None
        assert out.error_message is not None


# ── Tests — model failures ───────────────────────────────────────────────────

class TestSmaugModelFailures:
    """Tests for loading and inference failures."""

    def test_model_load_failure_returns_error(self, tmp_path: Path):
        img_path = _create_test_image(tmp_path / "test.png")
        inp = SmaugDetectionInput(image_path=str(img_path))

        with patch.object(
            ai_detect,
            "_load_detector",
            side_effect=RuntimeError("snapshot_download failed: connection error"),
        ):
            out = ai_detect.run(inp)

        assert out.status == ProcessingStatus.ERROR
        assert "Model loading failed" in out.error_message

    def test_inference_failure_returns_error(self, tmp_path: Path):
        img_path = _create_test_image(tmp_path / "test.png")
        inp = SmaugDetectionInput(image_path=str(img_path))

        mock_detector = MagicMock(side_effect=RuntimeError("CUDA OOM"))
        with patch.object(
            ai_detect,
            "_load_detector",
            return_value=(mock_detector, None),
        ):
            out = ai_detect.run(inp)

        assert out.status == ProcessingStatus.ERROR
        assert "Inference failed" in out.error_message

    def test_nonfinite_score_returns_error(self, tmp_path: Path):
        img_path = _create_test_image(tmp_path / "test.png")
        inp = SmaugDetectionInput(image_path=str(img_path))

        mock_detector = MagicMock(return_value=float("nan"))
        with patch.object(
            ai_detect,
            "_load_detector",
            return_value=(mock_detector, None),
        ):
            out = ai_detect.run(inp)

        assert out.status == ProcessingStatus.ERROR
        assert "non-finite" in out.error_message.lower()

    def test_out_of_range_score_returns_error(self, tmp_path: Path):
        img_path = _create_test_image(tmp_path / "test.png")
        inp = SmaugDetectionInput(image_path=str(img_path))

        mock_detector = MagicMock(return_value=1.5)  # out of [0, 1]
        with patch.object(
            ai_detect,
            "_load_detector",
            return_value=(mock_detector, None),
        ):
            out = ai_detect.run(inp)

        assert out.status == ProcessingStatus.ERROR
        assert "out-of-range" in out.error_message.lower()


# ── Tests — output serialisation ─────────────────────────────────────────────

class TestSmaugSerialization:
    """Ensure outputs can be serialised to JSON (required for contract interop)."""

    def test_success_output_serializes(self, tmp_path: Path, mock_smaug):
        img_path = _create_test_image(tmp_path / "test.png")
        inp = SmaugDetectionInput(image_path=str(img_path))
        out = ai_detect.run(inp)

        json_str = out.model_dump_json()
        assert '"status":"success"' in json_str
        assert '"ai_probability"' in json_str
        assert '"label"' in json_str

    def test_error_output_serializes(self, mock_smaug):
        inp = SmaugDetectionInput(image_path="/nonexistent.png")
        out = ai_detect.run(inp)

        json_str = out.model_dump_json()
        assert '"status":"error"' in json_str
        assert '"error_message"' in json_str

