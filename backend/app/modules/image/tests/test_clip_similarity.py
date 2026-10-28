"""
Unit tests for the CLIP claim-image similarity component.

All model loading and inference is mocked — these tests never download weights.
To run a real-model smoke test, use ``run_clip.py`` instead.

Run with::

    pytest backend/app/modules/image/tests/test_clip_similarity.py -v

Or from inside the Docker container::

    pytest app/modules/image/tests/test_clip_similarity.py -v
"""

from __future__ import annotations

import os
import math
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch
from PIL import Image

from app.modules.image.contracts import (
    ClipSimilarityInput,
    ClipSimilarityOutput,
    ProcessingStatus,
)
from app.modules.image import similarity


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


def _make_mock_model_outputs(cosine: float = 0.75, logit: float = 18.5):
    """Return a mock CLIPModel forward-pass output namespace."""
    d = 512
    # Build normalised embeddings whose cosine similarity equals *cosine*.
    image_vec = torch.randn(1, d)
    image_vec = image_vec / image_vec.norm(dim=-1, keepdim=True)
    # Construct text_vec so that (image_vec . text_vec) = cosine.
    # Start with the image_vec direction (gives cosine=1), scale, and add
    # an orthogonal component to reach the exact target cosine.
    text_vec = image_vec.clone() * cosine
    ortho = torch.randn(1, d)
    ortho = ortho - (ortho @ image_vec.T) * image_vec  # Gram-Schmidt
    ortho = ortho / ortho.norm(dim=-1, keepdim=True)
    remaining = max(0.0, 1.0 - cosine ** 2) ** 0.5
    text_vec = text_vec + remaining * ortho
    text_vec = text_vec / text_vec.norm(dim=-1, keepdim=True)

    return SimpleNamespace(
        logits_per_image=torch.tensor([[logit]]),
        image_embeds=image_vec,
        text_embeds=text_vec,
    )


# ── Reset singleton between tests ───────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_singleton():
    """Clear the module-level singleton so each test starts clean."""
    similarity._model = None
    similarity._processor = None
    similarity._device = None
    similarity._model_revision = None
    yield
    similarity._model = None
    similarity._processor = None
    similarity._device = None
    similarity._model_revision = None


@pytest.fixture()
def mock_clip():
    """Patch ``_load_model`` to return mocked CLIP model + processor."""
    mock_model = MagicMock()
    mock_model.eval.return_value = None
    mock_model.to.return_value = mock_model
    mock_model.config._commit_hash = "abc123test"

    mock_outputs = _make_mock_model_outputs(cosine=0.75, logit=18.5)
    mock_model.__call__ = MagicMock(return_value=mock_outputs)
    mock_model.return_value = mock_outputs

    mock_proc = MagicMock()
    mock_proc.return_value = {
        "input_ids": torch.zeros(1, 10, dtype=torch.long),
        "attention_mask": torch.ones(1, 10, dtype=torch.long),
        "pixel_values": torch.randn(1, 3, 224, 224),
    }

    device = torch.device("cpu")

    with patch.object(
        similarity,
        "_load_model",
        return_value=(mock_model, mock_proc, device, "abc123test"),
    ):
        yield mock_model, mock_proc


# ── Tests ────────────────────────────────────────────────────────────────────

class TestClipSimilarityValidInputs:
    """Tests with valid image + valid claim text."""

    def test_returns_success(self, tmp_path: Path, mock_clip):
        img_path = _create_test_image(tmp_path / "test.png")
        inp = ClipSimilarityInput(image_path=str(img_path), claim_text="A green field")
        out = similarity.run(inp)

        assert isinstance(out, ClipSimilarityOutput)
        assert out.status == ProcessingStatus.SUCCESS

    def test_similarity_score_is_finite(self, tmp_path: Path, mock_clip):
        img_path = _create_test_image(tmp_path / "test.png")
        inp = ClipSimilarityInput(image_path=str(img_path), claim_text="A green field")
        out = similarity.run(inp)

        assert out.similarity_score is not None
        assert math.isfinite(out.similarity_score)

    def test_logits_per_image_is_finite(self, tmp_path: Path, mock_clip):
        img_path = _create_test_image(tmp_path / "test.png")
        inp = ClipSimilarityInput(image_path=str(img_path), claim_text="A green field")
        out = similarity.run(inp)

        assert out.logits_per_image is not None
        assert math.isfinite(out.logits_per_image)

    def test_output_contract_fields(self, tmp_path: Path, mock_clip):
        img_path = _create_test_image(tmp_path / "test.png")
        inp = ClipSimilarityInput(image_path=str(img_path), claim_text="A green field")
        out = similarity.run(inp)

        assert out.comparison_method == "cosine_similarity"
        assert out.model_id == "openai/clip-vit-base-patch32"
        assert out.model_revision == "abc123test"
        assert out.error_message is None

    def test_similarity_in_valid_range(self, tmp_path: Path, mock_clip):
        img_path = _create_test_image(tmp_path / "test.png")
        inp = ClipSimilarityInput(image_path=str(img_path), claim_text="A green field")
        out = similarity.run(inp)

        assert -1.0 <= out.similarity_score <= 1.0


class TestClipSimilarityInvalidText:
    """Tests with empty or whitespace-only text."""

    def test_empty_text_rejected_by_pydantic(self):
        with pytest.raises(Exception):
            ClipSimilarityInput(image_path="/some/path.png", claim_text="")

    def test_whitespace_only_text_returns_error(self, tmp_path: Path, mock_clip):
        img_path = _create_test_image(tmp_path / "test.png")
        inp = ClipSimilarityInput(image_path=str(img_path), claim_text="   \t\n  ")
        out = similarity.run(inp)

        assert out.status == ProcessingStatus.ERROR
        assert out.similarity_score is None
        assert "non-empty" in out.error_message.lower() or "whitespace" in out.error_message.lower()


class TestClipSimilarityInvalidImage:
    """Tests with missing / invalid / corrupted image."""

    def test_missing_image_returns_error(self, mock_clip):
        inp = ClipSimilarityInput(
            image_path="/nonexistent/path/image.png",
            claim_text="A claim about something",
        )
        out = similarity.run(inp)

        assert out.status == ProcessingStatus.ERROR
        assert out.similarity_score is None
        assert "does not exist" in out.error_message.lower()

    def test_directory_instead_of_file_returns_error(self, tmp_path: Path, mock_clip):
        inp = ClipSimilarityInput(
            image_path=str(tmp_path),
            claim_text="A claim about something",
        )
        out = similarity.run(inp)

        assert out.status == ProcessingStatus.ERROR
        assert "directory" in out.error_message.lower()

    def test_corrupted_image_returns_error(self, tmp_path: Path, mock_clip):
        bad_path = _create_corrupted_file(tmp_path / "corrupted.png")
        inp = ClipSimilarityInput(
            image_path=str(bad_path),
            claim_text="A claim about something",
        )
        out = similarity.run(inp)

        assert out.status == ProcessingStatus.ERROR
        assert out.similarity_score is None
        assert out.error_message is not None


class TestClipSimilarityModelFailures:
    """Tests for model initialisation / inference failures."""

    def test_model_load_failure_returns_error(self, tmp_path: Path):
        img_path = _create_test_image(tmp_path / "test.png")
        inp = ClipSimilarityInput(image_path=str(img_path), claim_text="A claim")

        with patch.object(
            similarity,
            "_load_model",
            side_effect=RuntimeError("CUDA out of memory"),
        ):
            out = similarity.run(inp)

        assert out.status == ProcessingStatus.ERROR
        assert "Model loading failed" in out.error_message

    def test_inference_failure_returns_error(self, tmp_path: Path):
        img_path = _create_test_image(tmp_path / "test.png")
        inp = ClipSimilarityInput(image_path=str(img_path), claim_text="A claim")

        mock_model = MagicMock()
        mock_model.side_effect = RuntimeError("Inference exploded")
        mock_model.__call__ = MagicMock(
            side_effect=RuntimeError("Inference exploded")
        )
        mock_proc = MagicMock()
        mock_proc.return_value = {
            "input_ids": torch.zeros(1, 10, dtype=torch.long),
            "attention_mask": torch.ones(1, 10, dtype=torch.long),
            "pixel_values": torch.randn(1, 3, 224, 224),
        }
        device = torch.device("cpu")

        with patch.object(
            similarity,
            "_load_model",
            return_value=(mock_model, mock_proc, device, None),
        ):
            out = similarity.run(inp)

        assert out.status == ProcessingStatus.ERROR
        assert "Inference failed" in out.error_message


class TestClipSimilarityOutputSerialization:
    """Ensure the output can be serialized to JSON (required for contract interop)."""

    def test_success_output_serializes(self, tmp_path: Path, mock_clip):
        img_path = _create_test_image(tmp_path / "test.png")
        inp = ClipSimilarityInput(image_path=str(img_path), claim_text="A green field")
        out = similarity.run(inp)

        json_str = out.model_dump_json()
        assert '"status":"success"' in json_str
        assert '"similarity_score"' in json_str

    def test_error_output_serializes(self, mock_clip):
        inp = ClipSimilarityInput(
            image_path="/nonexistent.png", claim_text="Hello"
        )
        out = similarity.run(inp)

        json_str = out.model_dump_json()
        assert '"status":"error"' in json_str
        assert '"error_message"' in json_str
