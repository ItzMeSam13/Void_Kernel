"""
Unit tests for the PaddleOCR text extraction component (Module 2).

All engine loading and inference is mocked — these tests never download OCR weights.
To run a real-model smoke test, use ``run_ocr.py`` instead.

Covers:
- Valid image with text (3.x predict API and 2.x ocr API).
- Valid image with no text (returns NO_TEXT_DETECTED, not an error).
- Missing image path (returns ERROR).
- Directory path (returns ERROR).
- Pipeline initialization failure (returns ERROR).
- Inference failure (returns ERROR).
- Output contract serialization.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image

from app.modules.image.contracts import OcrInput, OcrOutput, OcrStatus, OcrTextRegion
from app.modules.image import ocr


def _create_test_image(path: Path, size: tuple[int, int] = (64, 64)) -> Path:
    """Write a small valid PNG to *path*."""
    img = Image.new("RGB", size, color=(128, 200, 50))
    img.save(path)
    return path


class TestOcrValidInputs(unittest.TestCase):
    """Tests with valid image input."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.img_path = _create_test_image(Path(self.temp_dir.name) / "test.png")
        # Reset singleton state
        ocr._ocr_pipeline = None
        ocr._ocr_api_version = None

    def tearDown(self):
        self.temp_dir.cleanup()
        ocr._ocr_pipeline = None
        ocr._ocr_api_version = None

    def test_text_detected_3x_api(self):
        """Simulate PaddleOCR 3.x predict() output."""
        mock_pipeline = MagicMock()
        mock_res = {
            "rec_texts": ["BREAKING", "NEWS"],
            "rec_scores": [0.99, 0.95],
            "rec_polys": [
                [[0, 0], [10, 0], [10, 5], [0, 5]],
                [[0, 10], [10, 10], [10, 15], [0, 15]],
            ],
        }
        mock_pipeline.predict.return_value = [mock_res]

        with patch.object(ocr, "_load_pipeline", return_value=(mock_pipeline, "3x")):
            out = ocr.run(OcrInput(image_path=str(self.img_path)))

        self.assertEqual(out.status, OcrStatus.TEXT_DETECTED)
        self.assertEqual(len(out.regions), 2)
        self.assertEqual(out.regions[0].text, "BREAKING")
        self.assertEqual(out.regions[1].text, "NEWS")
        self.assertEqual(out.combined_text, "BREAKING\nNEWS")

    def test_text_detected_2x_api(self):
        """Simulate PaddleOCR 2.x ocr() output."""
        mock_pipeline = MagicMock()
        mock_pipeline.ocr.return_value = [[
            [[[0, 0], [10, 0], [10, 5], [0, 5]], ("HEADLINE", 0.98)],
        ]]

        with patch.object(ocr, "_load_pipeline", return_value=(mock_pipeline, "2x")):
            out = ocr.run(OcrInput(image_path=str(self.img_path)))

        self.assertEqual(out.status, OcrStatus.TEXT_DETECTED)
        self.assertEqual(len(out.regions), 1)
        self.assertEqual(out.regions[0].text, "HEADLINE")
        self.assertEqual(out.combined_text, "HEADLINE")

    def test_no_text_detected_is_valid_success(self):
        """Image with no text returns NO_TEXT_DETECTED, not ERROR."""
        mock_pipeline = MagicMock()
        mock_pipeline.predict.return_value = []

        with patch.object(ocr, "_load_pipeline", return_value=(mock_pipeline, "3x")):
            out = ocr.run(OcrInput(image_path=str(self.img_path)))

        self.assertEqual(out.status, OcrStatus.NO_TEXT_DETECTED)
        self.assertEqual(out.regions, [])
        self.assertEqual(out.combined_text, "")
        self.assertIsNone(out.error_message)


class TestOcrInvalidInputs(unittest.TestCase):
    """Tests with missing or invalid image input."""

    def setUp(self):
        ocr._ocr_pipeline = None
        ocr._ocr_api_version = None

    def tearDown(self):
        ocr._ocr_pipeline = None
        ocr._ocr_api_version = None

    def test_missing_image_returns_error(self):
        out = ocr.run(OcrInput(image_path="/nonexistent/path/fake.png"))
        self.assertEqual(out.status, OcrStatus.ERROR)
        self.assertIn("does not exist", out.error_message.lower())

    def test_directory_instead_of_file_returns_error(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            out = ocr.run(OcrInput(image_path=tmp_dir))
            self.assertEqual(out.status, OcrStatus.ERROR)
            self.assertIn("directory", out.error_message.lower())


class TestOcrFailures(unittest.TestCase):
    """Tests for pipeline initialization and inference failures."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.img_path = _create_test_image(Path(self.temp_dir.name) / "test.png")
        ocr._ocr_pipeline = None
        ocr._ocr_api_version = None

    def tearDown(self):
        self.temp_dir.cleanup()
        ocr._ocr_pipeline = None
        ocr._ocr_api_version = None

    def test_load_pipeline_failure_returns_error(self):
        with patch.object(ocr, "_load_pipeline", side_effect=RuntimeError("Paddle initialization failed")):
            out = ocr.run(OcrInput(image_path=str(self.img_path)))

        self.assertEqual(out.status, OcrStatus.ERROR)
        self.assertIn("Paddle initialization failed", out.error_message)

    def test_inference_failure_returns_error(self):
        mock_pipeline = MagicMock()
        mock_pipeline.predict.side_effect = RuntimeError("Paddle execution failed")

        with patch.object(ocr, "_load_pipeline", return_value=(mock_pipeline, "3x")):
            out = ocr.run(OcrInput(image_path=str(self.img_path)))

        self.assertEqual(out.status, OcrStatus.ERROR)
        self.assertIn("Paddle execution failed", out.error_message)


class TestOcrSerialization(unittest.TestCase):
    """Test JSON serialization of OcrOutput."""

    def test_serialization(self):
        out = OcrOutput(
            status=OcrStatus.TEXT_DETECTED,
            regions=[OcrTextRegion(text="Hello", confidence=0.99)],
            combined_text="Hello",
        )
        json_str = out.model_dump_json()
        self.assertIn('"status":"text_detected"', json_str)
        self.assertIn('"combined_text":"Hello"', json_str)


if __name__ == "__main__":
    unittest.main()

