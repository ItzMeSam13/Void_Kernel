"""
Unit tests for the BLIP image captioning component.

All model loading and inference is mocked — these tests never download weights.
To run a real-model smoke test, use ``run_blip.py`` instead.

Run with::

    pytest backend/app/modules/image/tests/test_blip_caption.py -v

Or from inside the Docker container::

    pytest app/modules/image/tests/test_blip_caption.py -v
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import torch
from PIL import Image

from app.modules.image.contracts import (
    BlipCaptionInput,
    BlipCaptionOutput,
    ProcessingStatus,
)
from app.modules.image import caption


# ── Helpers ──────────────────────────────────────────────────────────────────

def _create_test_image(path: Path, size: tuple[int, int] = (64, 64), mode: str = "RGB") -> Path:
    """Write a small valid PNG to *path* in the given colour mode."""
    img = Image.new(mode, size, color=(128, 200, 50) if mode == "RGB" else 128)
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
    caption._model = None
    caption._processor = None
    caption._device = None
    caption._model_revision = None
    yield
    caption._model = None
    caption._processor = None
    caption._device = None
    caption._model_revision = None


@pytest.fixture()
def mock_blip():
    """Patch ``_load_model`` to return a mocked BLIP model + processor.

    The mocked model's ``generate()`` returns a tensor of token IDs, and the
    mocked processor's ``decode()`` returns a fixed caption string.
    """
    mock_model = MagicMock()
    mock_model.eval.return_value = None
    mock_model.to.return_value = mock_model
    mock_model.config._commit_hash = "blip_test_rev"

    # model.generate() returns a tensor of token IDs.
    mock_model.generate.return_value = torch.tensor([[101, 1037, 3899, 102]])

    mock_proc = MagicMock()
    # processor(images=..., return_tensors="pt") returns pixel_values.
    mock_proc.return_value = {
        "pixel_values": torch.randn(1, 3, 384, 384),
    }
    # processor.decode() turns token IDs into a caption string.
    mock_proc.decode.return_value = "a dog sitting on a bench"

    device = torch.device("cpu")

    with patch.object(
        caption,
        "_load_model",
        return_value=(mock_model, mock_proc, device, "blip_test_rev"),
    ):
        yield mock_model, mock_proc


# ── Tests ────────────────────────────────────────────────────────────────────

class TestBlipCaptionValidInputs:
    """Tests with valid image input."""

    def test_returns_success(self, tmp_path: Path, mock_blip):
        img_path = _create_test_image(tmp_path / "test.png")
        inp = BlipCaptionInput(image_path=str(img_path))
        out = caption.run(inp)

        assert isinstance(out, BlipCaptionOutput)
        assert out.status == ProcessingStatus.SUCCESS

    def test_caption_is_nonempty_string(self, tmp_path: Path, mock_blip):
        img_path = _create_test_image(tmp_path / "test.png")
        inp = BlipCaptionInput(image_path=str(img_path))
        out = caption.run(inp)

        assert out.caption is not None
        assert isinstance(out.caption, str)
        assert len(out.caption.strip()) > 0

    def test_output_contract_fields(self, tmp_path: Path, mock_blip):
        img_path = _create_test_image(tmp_path / "test.png")
        inp = BlipCaptionInput(image_path=str(img_path))
        out = caption.run(inp)

        assert out.model_id == "Salesforce/blip-image-captioning-base"
        assert out.model_revision == "blip_test_rev"
        assert out.error_message is None

    def test_rgba_image_converted_to_rgb(self, tmp_path: Path, mock_blip):
        """RGBA images should be handled (converted to RGB internally)."""
        img_path = tmp_path / "rgba.png"
        img = Image.new("RGBA", (64, 64), color=(128, 200, 50, 255))
        img.save(img_path)

        inp = BlipCaptionInput(image_path=str(img_path))
        out = caption.run(inp)

        assert out.status == ProcessingStatus.SUCCESS
        assert out.caption is not None

    def test_grayscale_image_converted_to_rgb(self, tmp_path: Path, mock_blip):
        """Grayscale (L) images should be handled (converted to RGB internally)."""
        img_path = _create_test_image(tmp_path / "gray.png", mode="L")
        inp = BlipCaptionInput(image_path=str(img_path))
        out = caption.run(inp)

        assert out.status == ProcessingStatus.SUCCESS
        assert out.caption is not None


class TestBlipCaptionInvalidImage:
    """Tests with missing / invalid / corrupted image."""

    def test_missing_image_returns_error(self, mock_blip):
        inp = BlipCaptionInput(image_path="/nonexistent/path/image.png")
        out = caption.run(inp)

        assert out.status == ProcessingStatus.ERROR
        assert out.caption is None
        assert "does not exist" in out.error_message.lower()

    def test_directory_instead_of_file_returns_error(self, tmp_path: Path, mock_blip):
        inp = BlipCaptionInput(image_path=str(tmp_path))
        out = caption.run(inp)

        assert out.status == ProcessingStatus.ERROR
        assert "directory" in out.error_message.lower()

    def test_corrupted_image_returns_error(self, tmp_path: Path, mock_blip):
        bad_path = _create_corrupted_file(tmp_path / "corrupted.png")
        inp = BlipCaptionInput(image_path=str(bad_path))
        out = caption.run(inp)

        assert out.status == ProcessingStatus.ERROR
        assert out.caption is None
        assert out.error_message is not None


class TestBlipCaptionModelFailures:
    """Tests for model initialisation / inference failures."""

    def test_model_load_failure_returns_error(self, tmp_path: Path):
        img_path = _create_test_image(tmp_path / "test.png")
        inp = BlipCaptionInput(image_path=str(img_path))

        with patch.object(
            caption,
            "_load_model",
            side_effect=RuntimeError("CUDA out of memory"),
        ):
            out = caption.run(inp)

        assert out.status == ProcessingStatus.ERROR
        assert "Model loading failed" in out.error_message

    def test_inference_failure_returns_error(self, tmp_path: Path):
        img_path = _create_test_image(tmp_path / "test.png")
        inp = BlipCaptionInput(image_path=str(img_path))

        mock_model = MagicMock()
        mock_model.generate.side_effect = RuntimeError("Inference exploded")

        mock_proc = MagicMock()
        mock_proc.return_value = {
            "pixel_values": torch.randn(1, 3, 384, 384),
        }
        device = torch.device("cpu")

        with patch.object(
            caption,
            "_load_model",
            return_value=(mock_model, mock_proc, device, None),
        ):
            out = caption.run(inp)

        assert out.status == ProcessingStatus.ERROR
        assert "Inference failed" in out.error_message

    def test_empty_caption_returns_error(self, tmp_path: Path):
        """If the model generates an empty string, report error, don't pretend success."""
        img_path = _create_test_image(tmp_path / "test.png")
        inp = BlipCaptionInput(image_path=str(img_path))

        mock_model = MagicMock()
        mock_model.generate.return_value = torch.tensor([[101, 102]])

        mock_proc = MagicMock()
        mock_proc.return_value = {
            "pixel_values": torch.randn(1, 3, 384, 384),
        }
        # Decode returns empty after stripping special tokens.
        mock_proc.decode.return_value = "   "
        device = torch.device("cpu")

        with patch.object(
            caption,
            "_load_model",
            return_value=(mock_model, mock_proc, device, None),
        ):
            out = caption.run(inp)

        assert out.status == ProcessingStatus.ERROR
        assert "empty caption" in out.error_message.lower()


class TestBlipCaptionOutputSerialization:
    """Ensure the output can be serialized to JSON (required for contract interop)."""

    def test_success_output_serializes(self, tmp_path: Path, mock_blip):
        img_path = _create_test_image(tmp_path / "test.png")
        inp = BlipCaptionInput(image_path=str(img_path))
        out = caption.run(inp)

        json_str = out.model_dump_json()
        assert '"status":"success"' in json_str
        assert '"caption"' in json_str

    def test_error_output_serializes(self, mock_blip):
        inp = BlipCaptionInput(image_path="/nonexistent.png")
        out = caption.run(inp)

        json_str = out.model_dump_json()
        assert '"status":"error"' in json_str
        assert '"error_message"' in json_str
