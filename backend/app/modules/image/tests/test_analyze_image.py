"""
Unit tests for the ``analyze_image`` composition layer (Module 2).

All sub-component ``run()`` functions (BLIP, CLIP, PaddleOCR, Smaug) are
mocked — these tests never download model weights or run GPU kernels.

Covers all test matrix requirements from the task specification:
1. Normal execution — all four components return valid findings.
2. Optional claim — claim passed to CLIP; skipped with typed reason when absent;
   OCR and BLIP text never substituted for an absent claim.
3. OCR outcomes — text detected, no_text_detected valid success, OCR error isolated.
4. Component failures — BLIP fail, CLIP fail, Smaug fail, multiple independent fails.
5. Input validation — missing/invalid image path returns error findings.
6. Public interface — video frame input compatibility, model_dump() support.
7. Canonical run() interface — run(ImageInput) produces identical findings.
8. Output serialization — JSON round-trip compatibility.

Compatible with both:
    python -m unittest app.modules.image.tests.test_analyze_image -v
and:
    pytest backend/app/modules/image/tests/test_analyze_image.py -v
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image

from app.modules.image.contracts import (
    BlipCaptionOutput,
    ClipSimilarityOutput,
    ClipSkippedReason,
    ImageFindings,
    ImageInput,
    OcrOutput,
    OcrStatus,
    OcrTextRegion,
    ProcessingStatus,
    SmaugDetectionOutput,
)
from app.modules.image.analyze_image import analyze_image
from app.modules.image.run import run as module_run


# ── Mock Factory Helpers ─────────────────────────────────────────────────────

def _create_test_image(path: Path, size: tuple[int, int] = (64, 64)) -> Path:
    """Write a small valid PNG to *path*."""
    img = Image.new("RGB", size, color=(128, 200, 50))
    img.save(path)
    return path


def _mock_blip_success() -> BlipCaptionOutput:
    return BlipCaptionOutput(
        status=ProcessingStatus.SUCCESS,
        caption="a cat sitting on a car",
        model_id="Salesforce/blip-image-captioning-base",
        model_revision="test_blip_rev",
    )


def _mock_clip_success() -> ClipSimilarityOutput:
    return ClipSimilarityOutput(
        status=ProcessingStatus.SUCCESS,
        similarity_score=0.75231,
        logits_per_image=18.52,
        comparison_method="cosine_similarity",
        model_id="openai/clip-vit-base-patch32",
        model_revision="test_clip_rev",
    )


def _mock_ocr_text_detected() -> OcrOutput:
    return OcrOutput(
        status=OcrStatus.TEXT_DETECTED,
        regions=[
            OcrTextRegion(
                text="BREAKING NEWS",
                confidence=0.985,
                bounding_box=[[10.0, 10.0], [100.0, 10.0], [100.0, 30.0], [10.0, 30.0]],
            ),
        ],
        combined_text="BREAKING NEWS",
    )


def _mock_ocr_no_text() -> OcrOutput:
    return OcrOutput(
        status=OcrStatus.NO_TEXT_DETECTED,
        regions=[],
        combined_text="",
    )


def _mock_smaug_success() -> SmaugDetectionOutput:
    return SmaugDetectionOutput(
        status=ProcessingStatus.SUCCESS,
        ai_probability=0.123456,
        label="not_flagged_as_ai_generated",
        detection_threshold=0.5,
        model_id="abacusai/Smaug-AI-Image-Detector",
        model_revision="test_smaug_rev",
    )


# ── Test Suite ───────────────────────────────────────────────────────────────

class TestAnalyzeImageNormalExecution(unittest.TestCase):
    """Normal execution with all four components succeeding."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.img_path = _create_test_image(Path(self.temp_dir.name) / "test.png")

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("app.modules.image.caption.run", return_value=_mock_blip_success())
    @patch("app.modules.image.similarity.run", return_value=_mock_clip_success())
    @patch("app.modules.image.ocr.run", return_value=_mock_ocr_text_detected())
    @patch("app.modules.image.ai_detect.run", return_value=_mock_smaug_success())
    def test_all_components_return_valid_findings(
        self, mock_smaug, mock_ocr, mock_clip, mock_blip
    ):
        result = analyze_image(str(self.img_path), claim_text="a photo of a cat")

        self.assertIsInstance(result, ImageFindings)
        self.assertEqual(result.image_path, str(self.img_path.resolve()))
        self.assertEqual(result.claim_text, "a photo of a cat")

        # BLIP findings
        self.assertIsNotNone(result.blip)
        self.assertEqual(result.blip.status, ProcessingStatus.SUCCESS)
        self.assertEqual(result.blip.caption, "a cat sitting on a car")

        # CLIP findings
        self.assertIsNotNone(result.clip)
        self.assertEqual(result.clip.status, ProcessingStatus.SUCCESS)
        self.assertEqual(result.clip.similarity_score, 0.75231)
        self.assertIsNone(result.clip_skipped_reason)

        # OCR findings
        self.assertIsNotNone(result.ocr)
        self.assertEqual(result.ocr.status, OcrStatus.TEXT_DETECTED)
        self.assertEqual(result.ocr.combined_text, "BREAKING NEWS")
        self.assertEqual(len(result.ocr.regions), 1)

        # Smaug findings
        self.assertIsNotNone(result.smaug)
        self.assertEqual(result.smaug.status, ProcessingStatus.SUCCESS)
        self.assertEqual(result.smaug.ai_probability, 0.123456)


class TestAnalyzeImageOptionalClaim(unittest.TestCase):
    """CLIP skip semantics when claim is absent, empty, or whitespace."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.img_path = _create_test_image(Path(self.temp_dir.name) / "test.png")

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("app.modules.image.caption.run", return_value=_mock_blip_success())
    @patch("app.modules.image.similarity.run")
    @patch("app.modules.image.ocr.run", return_value=_mock_ocr_text_detected())
    @patch("app.modules.image.ai_detect.run", return_value=_mock_smaug_success())
    def test_no_claim_skips_clip_and_runs_others(
        self, mock_smaug, mock_ocr, mock_clip, mock_blip
    ):
        result = analyze_image(str(self.img_path), claim_text=None)

        self.assertIsNone(result.clip)
        self.assertEqual(result.clip_skipped_reason, ClipSkippedReason.NO_CLAIM_PROVIDED)
        mock_clip.assert_not_called()

        # Others must still run successfully
        self.assertEqual(result.blip.status, ProcessingStatus.SUCCESS)
        self.assertEqual(result.ocr.status, OcrStatus.TEXT_DETECTED)
        self.assertEqual(result.smaug.status, ProcessingStatus.SUCCESS)

    @patch("app.modules.image.caption.run", return_value=_mock_blip_success())
    @patch("app.modules.image.similarity.run")
    @patch("app.modules.image.ocr.run", return_value=_mock_ocr_text_detected())
    @patch("app.modules.image.ai_detect.run", return_value=_mock_smaug_success())
    def test_empty_and_whitespace_claim_skips_clip(
        self, mock_smaug, mock_ocr, mock_clip, mock_blip
    ):
        for empty_val in ("", "   ", "\t\n  "):
            result = analyze_image(str(self.img_path), claim_text=empty_val)
            self.assertIsNone(result.clip)
            self.assertEqual(result.clip_skipped_reason, ClipSkippedReason.NO_CLAIM_PROVIDED)
            mock_clip.assert_not_called()

    @patch("app.modules.image.caption.run", return_value=_mock_blip_success())
    @patch("app.modules.image.similarity.run")
    @patch("app.modules.image.ocr.run", return_value=_mock_ocr_text_detected())
    @patch("app.modules.image.ai_detect.run", return_value=_mock_smaug_success())
    def test_ocr_and_blip_text_never_substituted_for_absent_claim(
        self, mock_smaug, mock_ocr, mock_clip, mock_blip
    ):
        result = analyze_image(str(self.img_path), claim_text=None)

        self.assertIsNone(result.claim_text)
        self.assertIsNone(result.clip)
        # Even though OCR detected "BREAKING NEWS" and BLIP produced caption,
        # neither was fed to CLIP
        mock_clip.assert_not_called()


class TestAnalyzeImageOcrOutcomes(unittest.TestCase):
    """OCR variations: no text detected vs text detected vs OCR error."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.img_path = _create_test_image(Path(self.temp_dir.name) / "test.png")

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("app.modules.image.caption.run", return_value=_mock_blip_success())
    @patch("app.modules.image.ocr.run", return_value=_mock_ocr_no_text())
    @patch("app.modules.image.ai_detect.run", return_value=_mock_smaug_success())
    def test_ocr_no_text_detected_is_valid_success(
        self, mock_smaug, mock_ocr, mock_blip
    ):
        result = analyze_image(str(self.img_path))

        self.assertIsNotNone(result.ocr)
        self.assertEqual(result.ocr.status, OcrStatus.NO_TEXT_DETECTED)
        self.assertEqual(result.ocr.combined_text, "")
        self.assertEqual(result.ocr.regions, [])

        # Non-OCR components still succeed
        self.assertEqual(result.blip.status, ProcessingStatus.SUCCESS)
        self.assertEqual(result.smaug.status, ProcessingStatus.SUCCESS)

    @patch("app.modules.image.caption.run", return_value=_mock_blip_success())
    @patch("app.modules.image.ocr.run", return_value=OcrOutput(status=OcrStatus.ERROR, error_message="OCR engine crashed"))
    @patch("app.modules.image.ai_detect.run", return_value=_mock_smaug_success())
    def test_ocr_error_does_not_suppress_other_components(
        self, mock_smaug, mock_ocr, mock_blip
    ):
        result = analyze_image(str(self.img_path))

        self.assertEqual(result.ocr.status, OcrStatus.ERROR)
        self.assertIn("OCR engine crashed", result.ocr.error_message)

        # Other components succeed
        self.assertEqual(result.blip.status, ProcessingStatus.SUCCESS)
        self.assertEqual(result.smaug.status, ProcessingStatus.SUCCESS)


class TestAnalyzeImageComponentFailures(unittest.TestCase):
    """Failure isolation: each component failure is captured independently."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.img_path = _create_test_image(Path(self.temp_dir.name) / "test.png")

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("app.modules.image.caption.run", side_effect=RuntimeError("BLIP weights corrupted"))
    @patch("app.modules.image.similarity.run", return_value=_mock_clip_success())
    @patch("app.modules.image.ocr.run", return_value=_mock_ocr_text_detected())
    @patch("app.modules.image.ai_detect.run", return_value=_mock_smaug_success())
    def test_blip_failure_isolated(
        self, mock_smaug, mock_ocr, mock_clip, mock_blip
    ):
        result = analyze_image(str(self.img_path), claim_text="valid claim")

        self.assertEqual(result.blip.status, ProcessingStatus.ERROR)
        self.assertIn("BLIP", result.blip.error_message)

        # Others untouched
        self.assertEqual(result.clip.status, ProcessingStatus.SUCCESS)
        self.assertEqual(result.ocr.status, OcrStatus.TEXT_DETECTED)
        self.assertEqual(result.smaug.status, ProcessingStatus.SUCCESS)

    @patch("app.modules.image.caption.run", return_value=_mock_blip_success())
    @patch("app.modules.image.similarity.run", side_effect=RuntimeError("CLIP OOM"))
    @patch("app.modules.image.ocr.run", return_value=_mock_ocr_text_detected())
    @patch("app.modules.image.ai_detect.run", return_value=_mock_smaug_success())
    def test_clip_failure_isolated(
        self, mock_smaug, mock_ocr, mock_clip, mock_blip
    ):
        result = analyze_image(str(self.img_path), claim_text="valid claim")

        self.assertEqual(result.clip.status, ProcessingStatus.ERROR)
        self.assertIn("CLIP", result.clip.error_message)

        # Others untouched
        self.assertEqual(result.blip.status, ProcessingStatus.SUCCESS)
        self.assertEqual(result.ocr.status, OcrStatus.TEXT_DETECTED)
        self.assertEqual(result.smaug.status, ProcessingStatus.SUCCESS)

    @patch("app.modules.image.caption.run", return_value=_mock_blip_success())
    @patch("app.modules.image.similarity.run", return_value=_mock_clip_success())
    @patch("app.modules.image.ocr.run", return_value=_mock_ocr_text_detected())
    @patch("app.modules.image.ai_detect.run", side_effect=RuntimeError("Smaug download timeout"))
    def test_smaug_failure_isolated(
        self, mock_smaug, mock_ocr, mock_clip, mock_blip
    ):
        result = analyze_image(str(self.img_path), claim_text="valid claim")

        self.assertEqual(result.smaug.status, ProcessingStatus.ERROR)
        self.assertIn("Smaug", result.smaug.error_message)

        # Others untouched
        self.assertEqual(result.blip.status, ProcessingStatus.SUCCESS)
        self.assertEqual(result.clip.status, ProcessingStatus.SUCCESS)
        self.assertEqual(result.ocr.status, OcrStatus.TEXT_DETECTED)

    @patch("app.modules.image.caption.run", side_effect=RuntimeError("BLIP fail"))
    @patch("app.modules.image.similarity.run", side_effect=RuntimeError("CLIP fail"))
    @patch("app.modules.image.ocr.run", return_value=_mock_ocr_text_detected())
    @patch("app.modules.image.ai_detect.run", side_effect=RuntimeError("Smaug fail"))
    def test_multiple_independent_failures(
        self, mock_smaug, mock_ocr, mock_clip, mock_blip
    ):
        result = analyze_image(str(self.img_path), claim_text="test")

        self.assertEqual(result.blip.status, ProcessingStatus.ERROR)
        self.assertEqual(result.clip.status, ProcessingStatus.ERROR)
        self.assertEqual(result.smaug.status, ProcessingStatus.ERROR)

        # OCR still succeeded
        self.assertEqual(result.ocr.status, OcrStatus.TEXT_DETECTED)
        self.assertEqual(result.ocr.combined_text, "BREAKING NEWS")


class TestAnalyzeImageInputValidation(unittest.TestCase):
    """Input validation: non-existent file, directory path."""

    def test_missing_image_path_returns_error_findings(self):
        bad_path = "/nonexistent/fake/file_that_does_not_exist_123.png"
        result = analyze_image(bad_path, claim_text="test")

        self.assertIsInstance(result, ImageFindings)
        self.assertEqual(result.blip.status, ProcessingStatus.ERROR)
        self.assertIn("does not exist", result.blip.error_message.lower())
        self.assertEqual(result.smaug.status, ProcessingStatus.ERROR)
        self.assertEqual(result.ocr.status, OcrStatus.ERROR)

    def test_directory_path_returns_error_findings(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = analyze_image(tmp_dir)

            self.assertIsInstance(result, ImageFindings)
            self.assertEqual(result.blip.status, ProcessingStatus.ERROR)
            self.assertIn("directory", result.blip.error_message.lower())
            self.assertEqual(result.smaug.status, ProcessingStatus.ERROR)
            self.assertEqual(result.ocr.status, OcrStatus.ERROR)


class TestAnalyzeImagePublicInterfaceAndInterop(unittest.TestCase):
    """Public interface compatibility with Video Module and Canonical run()."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.img_path = _create_test_image(Path(self.temp_dir.name) / "frame_001.png")

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("app.modules.image.caption.run", return_value=_mock_blip_success())
    @patch("app.modules.image.similarity.run", return_value=_mock_clip_success())
    @patch("app.modules.image.ocr.run", return_value=_mock_ocr_text_detected())
    @patch("app.modules.image.ai_detect.run", return_value=_mock_smaug_success())
    def test_video_module_per_frame_call_pattern(
        self, mock_smaug, mock_ocr, mock_clip, mock_blip
    ):
        """Video module calls: findings = analyze_image_fn(crop_path, claim_text); findings.model_dump()"""
        findings = analyze_image(str(self.img_path), "video title claim")
        dumped = findings.model_dump()

        self.assertIsInstance(dumped, dict)
        self.assertIn("blip", dumped)
        self.assertIn("clip", dumped)
        self.assertIn("ocr", dumped)
        self.assertIn("smaug", dumped)
        self.assertEqual(dumped["blip"]["status"], "success")

    @patch("app.modules.image.caption.run", return_value=_mock_blip_success())
    @patch("app.modules.image.similarity.run", return_value=_mock_clip_success())
    @patch("app.modules.image.ocr.run", return_value=_mock_ocr_text_detected())
    @patch("app.modules.image.ai_detect.run", return_value=_mock_smaug_success())
    def test_canonical_run_interface_equivalence(
        self, mock_smaug, mock_ocr, mock_clip, mock_blip
    ):
        """run(ImageInput) produces the identical ImageFindings result as analyze_image()."""
        inp = ImageInput(image_path=str(self.img_path), claim_text="video claim")
        result_run = module_run(inp)
        result_direct = analyze_image(str(self.img_path), claim_text="video claim")

        self.assertEqual(result_run.model_dump(), result_direct.model_dump())

    @patch("app.modules.image.caption.run", return_value=_mock_blip_success())
    @patch("app.modules.image.similarity.run", return_value=_mock_clip_success())
    @patch("app.modules.image.ocr.run", return_value=_mock_ocr_text_detected())
    @patch("app.modules.image.ai_detect.run", return_value=_mock_smaug_success())
    def test_json_serialization_round_trip(
        self, mock_smaug, mock_ocr, mock_clip, mock_blip
    ):
        """ImageFindings must be cleanly serializable to JSON."""
        findings = analyze_image(str(self.img_path), "test claim")
        json_str = findings.model_dump_json()
        parsed = json.loads(json_str)

        self.assertEqual(parsed["blip"]["caption"], "a cat sitting on a car")
        self.assertEqual(parsed["clip"]["similarity_score"], 0.75231)
        self.assertEqual(parsed["ocr"]["combined_text"], "BREAKING NEWS")
        self.assertEqual(parsed["smaug"]["ai_probability"], 0.123456)


if __name__ == "__main__":
    unittest.main()
