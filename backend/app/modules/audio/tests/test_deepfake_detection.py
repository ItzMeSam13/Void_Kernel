"""
Unit tests for the Wav2Vec2 synthetic-audio detection component.

All model loading and neural forward-passes are mocked — these tests never
download weights during test collection or execution.

To run a real-model smoke test, use ``run_deepfake.py`` instead.

Run with pytest::

    pytest app/modules/audio/tests/test_deepfake_detection.py -v

Or with Python's built-in unittest runner::

    python -m unittest app.modules.audio.tests.test_deepfake_detection
"""
from __future__ import annotations

import os
import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import torch
from pydantic import ValidationError

from app.modules.audio.contracts import (
    AudioDetectionInput,
    AudioDetectionOutput,
    AudioFindings,
    AudioInput,
    AudioWindowScore,
    DetectionStatus,
)
from app.modules.audio import deepfake_detection
from app.modules.audio import run as module_run


# ── Helpers ──────────────────────────────────────────────────────────────────

def _create_temp_audio(
    duration_sec: float = 1.0,
    sample_rate: int = 16000,
    frequency: float = 440.0,
    amplitude: float = 0.5,
) -> Path:
    """Create a temporary valid WAV file containing a sine tone."""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = Path(tmp.name)
    tmp.close()

    num_samples = int(duration_sec * sample_rate)
    with wave.open(str(tmp_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)

        samples = []
        for i in range(num_samples):
            val = int(32767.0 * amplitude * np.sin(2.0 * np.pi * frequency * (i / sample_rate)))
            samples.append(val)

        raw = np.array(samples, dtype=np.int16).tobytes()
        wf.writeframes(raw)

    return tmp_path


def _create_silent_wav(duration_sec: float = 1.0, sample_rate: int = 16000) -> Path:
    """Create a temporary WAV file containing pure digital silence."""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = Path(tmp.name)
    tmp.close()

    num_samples = int(duration_sec * sample_rate)
    with wave.open(str(tmp_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_samples)

    return tmp_path


def _make_mock_model(logits: torch.Tensor, id2label: dict | None = None) -> MagicMock:
    """Create a mock AutoModelForAudioClassification returning specified logits."""
    model = MagicMock()
    model.config = SimpleNamespace(
        id2label=id2label or {0: "fake", 1: "real"},
        label2id={"fake": 0, "real": 1},
    )
    outputs = SimpleNamespace(logits=logits)
    model.return_value = outputs
    return model


def _make_mock_fe(sampling_rate: int = 16000) -> MagicMock:
    """Create a mock AutoFeatureExtractor."""
    fe = MagicMock()
    fe.sampling_rate = sampling_rate
    fe.return_value = {
        "input_values": torch.zeros((1, 16000), dtype=torch.float32)
    }
    return fe


def _run_coro(coro):
    """Run a coroutine without requiring an OS socket-based event loop."""
    try:
        coro.send(None)
    except StopIteration as exc:
        return exc.value
    raise RuntimeError("Coroutine did not finish synchronously")


# ── Test Suite ───────────────────────────────────────────────────────────────

class TestDeepfakeAudioDetection(unittest.TestCase):
    """Test suite for Wav2Vec2 synthetic-audio detection component."""

    def setUp(self) -> None:
        deepfake_detection.reset_model()
        self._temp_files: list[Path] = []

    def tearDown(self) -> None:
        deepfake_detection.reset_model()
        for p in self._temp_files:
            if p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass

    def _get_temp_audio(self, duration_sec: float = 1.0, sample_rate: int = 16000) -> Path:
        p = _create_temp_audio(duration_sec=duration_sec, sample_rate=sample_rate)
        self._temp_files.append(p)
        return p

    def _get_silent_audio(self, duration_sec: float = 1.0) -> Path:
        p = _create_silent_wav(duration_sec=duration_sec)
        self._temp_files.append(p)
        return p

    # ── 1. Successful inference with fake prediction ─────────────────────────

    @patch("app.modules.audio.deepfake_detection.AutoModelForAudioClassification")
    @patch("app.modules.audio.deepfake_detection.AutoFeatureExtractor")
    def test_successful_inference_fake_prediction(
        self, mock_fe_cls: MagicMock, mock_model_cls: MagicMock
    ) -> None:
        # High logit for index 0 (fake), low logit for index 1 (real)
        mock_model = _make_mock_model(torch.tensor([[4.5, -2.1]]))
        mock_fe = _make_mock_fe()
        mock_model_cls.from_pretrained.return_value = mock_model
        mock_fe_cls.from_pretrained.return_value = mock_fe

        wav_path = self._get_temp_audio(duration_sec=1.5)
        inp = AudioDetectionInput(audio_path=str(wav_path))

        out = deepfake_detection.run(inp)

        self.assertEqual(out.status, DetectionStatus.SUCCESS)
        self.assertEqual(out.verdict, "synthetic_audio_signal_detected")
        self.assertEqual(out.predicted_label, "fake")
        self.assertGreater(out.fake_score, 0.90)
        self.assertLess(out.real_score, 0.10)
        self.assertAlmostEqual(out.fake_score + out.real_score, 1.0, places=3)
        self.assertEqual(len(out.window_scores), 1)
        self.assertEqual(out.window_scores[0].predicted_label, "fake")

    # ── 2. Successful inference with real prediction ─────────────────────────

    @patch("app.modules.audio.deepfake_detection.AutoModelForAudioClassification")
    @patch("app.modules.audio.deepfake_detection.AutoFeatureExtractor")
    def test_successful_inference_real_prediction(
        self, mock_fe_cls: MagicMock, mock_model_cls: MagicMock
    ) -> None:
        # Low logit for index 0 (fake), high logit for index 1 (real)
        mock_model = _make_mock_model(torch.tensor([[-3.2, 5.0]]))
        mock_fe = _make_mock_fe()
        mock_model_cls.from_pretrained.return_value = mock_model
        mock_fe_cls.from_pretrained.return_value = mock_fe

        wav_path = self._get_temp_audio(duration_sec=2.0)
        inp = AudioDetectionInput(audio_path=str(wav_path))

        out = deepfake_detection.run(inp)

        self.assertEqual(out.status, DetectionStatus.SUCCESS)
        self.assertEqual(out.verdict, "no_strong_signal_detected")
        self.assertEqual(out.predicted_label, "real")
        self.assertGreater(out.real_score, 0.90)
        self.assertLess(out.fake_score, 0.10)
        self.assertEqual(out.class_probabilities["real"], out.real_score)

    # ── 3. Ambiguous score yields inconclusive verdict ───────────────────────

    @patch("app.modules.audio.deepfake_detection.AutoModelForAudioClassification")
    @patch("app.modules.audio.deepfake_detection.AutoFeatureExtractor")
    def test_inconclusive_verdict_for_middle_probabilities(
        self, mock_fe_cls: MagicMock, mock_model_cls: MagicMock
    ) -> None:
        # Equal logits yield 50% fake, 50% real
        mock_model = _make_mock_model(torch.tensor([[0.0, 0.0]]))
        mock_fe = _make_mock_fe()
        mock_model_cls.from_pretrained.return_value = mock_model
        mock_fe_cls.from_pretrained.return_value = mock_fe

        wav_path = self._get_temp_audio()
        inp = AudioDetectionInput(audio_path=str(wav_path))

        out = deepfake_detection.run(inp)

        self.assertEqual(out.status, DetectionStatus.SUCCESS)
        self.assertEqual(out.verdict, "inconclusive")
        self.assertAlmostEqual(out.fake_score, 0.5, places=2)
        self.assertAlmostEqual(out.real_score, 0.5, places=2)

    # ── 4. Dynamic label mapping resolution ──────────────────────────────────

    def test_label_mapping_resolution_standard(self) -> None:
        id2label = {0: "fake", 1: "real"}
        fake_idx, real_idx = deepfake_detection._resolve_label_indices(id2label)
        self.assertEqual(fake_idx, 0)
        self.assertEqual(real_idx, 1)

    def test_label_mapping_resolution_inverted(self) -> None:
        id2label = {"0": "bonafide", "1": "synthetic"}
        fake_idx, real_idx = deepfake_detection._resolve_label_indices(id2label)
        self.assertEqual(fake_idx, 1)
        self.assertEqual(real_idx, 0)

    def test_label_mapping_resolution_invalid_raises(self) -> None:
        with self.assertRaises(ValueError):
            deepfake_detection._resolve_label_indices({0: "cat", 1: "dog"})

    # ── 5. Missing and empty file handling ───────────────────────────────────

    def test_missing_audio_file_returns_error(self) -> None:
        missing = Path(tempfile.gettempdir()) / "non_existent_audio_sample_9876.wav"
        if missing.exists():
            missing.unlink()

        inp = AudioDetectionInput(audio_path=str(missing))
        out = deepfake_detection.run(inp)

        self.assertEqual(out.status, DetectionStatus.ERROR)
        self.assertEqual(out.verdict, "not_assessed")
        self.assertIn("Audio file not found", out.error_message)

    def test_empty_audio_file_returns_error(self) -> None:
        empty = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        empty_path = Path(empty.name)
        empty.close()
        self._temp_files.append(empty_path)

        inp = AudioDetectionInput(audio_path=str(empty_path))
        out = deepfake_detection.run(inp)

        self.assertEqual(out.status, DetectionStatus.ERROR)
        self.assertIn("empty", out.error_message.lower())

    def test_directory_path_returns_error(self) -> None:
        tmp_dir = tempfile.mkdtemp()
        inp = AudioDetectionInput(audio_path=tmp_dir)
        out = deepfake_detection.run(inp)

        self.assertEqual(out.status, DetectionStatus.ERROR)
        self.assertIn("not a file", out.error_message.lower())
        os.rmdir(tmp_dir)

    # ── 6. Audio duration too short (< 0.25s) ────────────────────────────────

    @patch("app.modules.audio.deepfake_detection.AutoModelForAudioClassification")
    @patch("app.modules.audio.deepfake_detection.AutoFeatureExtractor")
    def test_too_short_audio_returns_not_assessed(
        self, mock_fe_cls: MagicMock, mock_model_cls: MagicMock
    ) -> None:
        mock_model = _make_mock_model(torch.tensor([[0.0, 0.0]]))
        mock_fe = _make_mock_fe()
        mock_model_cls.from_pretrained.return_value = mock_model
        mock_fe_cls.from_pretrained.return_value = mock_fe

        wav_path = self._get_temp_audio(duration_sec=0.1)
        inp = AudioDetectionInput(audio_path=str(wav_path))

        out = deepfake_detection.run(inp)

        self.assertEqual(out.status, DetectionStatus.NOT_ASSESSED)
        self.assertEqual(out.verdict, "not_assessed")
        self.assertIn("too short", out.error_message.lower())

    # ── 7. Silent audio handling ─────────────────────────────────────────────

    @patch("app.modules.audio.deepfake_detection.AutoModelForAudioClassification")
    @patch("app.modules.audio.deepfake_detection.AutoFeatureExtractor")
    def test_silent_audio_returns_silence_status(
        self, mock_fe_cls: MagicMock, mock_model_cls: MagicMock
    ) -> None:
        mock_model = _make_mock_model(torch.tensor([[0.0, 0.0]]))
        mock_fe = _make_mock_fe()
        mock_model_cls.from_pretrained.return_value = mock_model
        mock_fe_cls.from_pretrained.return_value = mock_fe

        silent_path = self._get_silent_audio(duration_sec=1.5)
        inp = AudioDetectionInput(audio_path=str(silent_path))

        out = deepfake_detection.run(inp)

        self.assertEqual(out.status, DetectionStatus.SILENCE_OR_EMPTY)
        self.assertEqual(out.verdict, "inconclusive")
        self.assertIn("silent", out.error_message.lower())

    # ── 8. Corrupt audio handling ────────────────────────────────────────────

    @patch("app.modules.audio.deepfake_detection.AutoModelForAudioClassification")
    @patch("app.modules.audio.deepfake_detection.AutoFeatureExtractor")
    def test_corrupt_audio_returns_error(
        self, mock_fe_cls: MagicMock, mock_model_cls: MagicMock
    ) -> None:
        mock_model = _make_mock_model(torch.tensor([[0.0, 0.0]]))
        mock_fe = _make_mock_fe()
        mock_model_cls.from_pretrained.return_value = mock_model
        mock_fe_cls.from_pretrained.return_value = mock_fe

        corrupt = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        corrupt.write(b"NOT_A_VALID_WAV_HEADER" * 10)
        corrupt_path = Path(corrupt.name)
        corrupt.close()
        self._temp_files.append(corrupt_path)

        inp = AudioDetectionInput(audio_path=str(corrupt_path))
        out = deepfake_detection.run(inp)

        self.assertEqual(out.status, DetectionStatus.ERROR)
        self.assertIn("decoding failed", out.error_message.lower())

    # ── 9. Non-finite logits rejection ───────────────────────────────────────

    @patch("app.modules.audio.deepfake_detection.AutoModelForAudioClassification")
    @patch("app.modules.audio.deepfake_detection.AutoFeatureExtractor")
    def test_non_finite_logits_rejected(
        self, mock_fe_cls: MagicMock, mock_model_cls: MagicMock
    ) -> None:
        # Return NaN logits
        mock_model = _make_mock_model(torch.tensor([[float("nan"), 1.0]]))
        mock_fe = _make_mock_fe()
        mock_model_cls.from_pretrained.return_value = mock_model
        mock_fe_cls.from_pretrained.return_value = mock_fe

        wav_path = self._get_temp_audio()
        inp = AudioDetectionInput(audio_path=str(wav_path))

        out = deepfake_detection.run(inp)

        self.assertEqual(out.status, DetectionStatus.ERROR)
        self.assertIn("non-finite logits", out.error_message.lower())

    # ── 10. Model loading failure ────────────────────────────────────────────

    @patch("app.modules.audio.deepfake_detection.AutoModelForAudioClassification")
    def test_model_loading_failure(self, mock_model_cls: MagicMock) -> None:
        mock_model_cls.from_pretrained.side_effect = RuntimeError("Failed to load weights from Hub")

        wav_path = self._get_temp_audio()
        inp = AudioDetectionInput(audio_path=str(wav_path))

        out = deepfake_detection.run(inp)

        self.assertEqual(out.status, DetectionStatus.ERROR)
        self.assertIn("Model initialization failed", out.error_message)

    # ── 11. Chunked inference on long audio ──────────────────────────────────

    @patch("app.modules.audio.deepfake_detection.AutoModelForAudioClassification")
    @patch("app.modules.audio.deepfake_detection.AutoFeatureExtractor")
    def test_long_recording_chunked_inference(
        self, mock_fe_cls: MagicMock, mock_model_cls: MagicMock
    ) -> None:
        # Create an 11-second audio
        wav_path = self._get_temp_audio(duration_sec=11.0)

        # Mock model outputs different logits for consecutive calls
        call_count = [0]
        def mock_forward(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return SimpleNamespace(logits=torch.tensor([[-2.0, 3.0]]))  # real
            elif call_count[0] == 2:
                return SimpleNamespace(logits=torch.tensor([[4.0, -1.0]]))  # fake
            else:
                return SimpleNamespace(logits=torch.tensor([[1.0, 1.0]]))   # 50/50

        mock_model = MagicMock()
        mock_model.config = SimpleNamespace(id2label={0: "fake", 1: "real"}, label2id={"fake": 0, "real": 1})
        mock_model.side_effect = mock_forward
        mock_fe = _make_mock_fe()
        mock_model_cls.from_pretrained.return_value = mock_model
        mock_fe_cls.from_pretrained.return_value = mock_fe

        inp = AudioDetectionInput(
            audio_path=str(wav_path),
            window_duration_sec=5.0,
            window_overlap_sec=1.0,
        )

        out = deepfake_detection.run(inp)

        self.assertEqual(out.status, DetectionStatus.SUCCESS)
        self.assertGreater(len(out.window_scores), 1)
        self.assertEqual(out.window_scores[0].start_sec, 0.0)
        self.assertEqual(out.window_scores[0].end_sec, 5.0)
        # Check that peak fake window influenced the aggregate
        self.assertGreater(out.fake_score, 0.5)

    # ── 12. Window score validation ──────────────────────────────────────────

    def test_window_score_validation(self) -> None:
        valid = AudioWindowScore(
            start_sec=0.0,
            end_sec=2.5,
            fake_score=0.8,
            real_score=0.2,
            predicted_label="fake",
        )
        self.assertEqual(valid.start_sec, 0.0)

        with self.assertRaises(ValidationError):
            AudioWindowScore(
                start_sec=5.0,
                end_sec=2.0,  # invalid: end < start
                fake_score=0.8,
                real_score=0.2,
                predicted_label="fake",
            )

    # ── 13. Singleton reuse and reset ────────────────────────────────────────

    @patch("app.modules.audio.deepfake_detection.AutoModelForAudioClassification")
    @patch("app.modules.audio.deepfake_detection.AutoFeatureExtractor")
    def test_model_singleton_reuse_and_reset(
        self, mock_fe_cls: MagicMock, mock_model_cls: MagicMock
    ) -> None:
        mock_m = MagicMock()
        mock_m.to.return_value = mock_m
        mock_fe = MagicMock()
        mock_model_cls.from_pretrained.return_value = mock_m
        mock_fe_cls.from_pretrained.return_value = mock_fe

        m1, fe1, dev1 = deepfake_detection.get_model()
        m2, fe2, dev2 = deepfake_detection.get_model()

        self.assertIs(m1, m2)
        self.assertIs(fe1, fe2)
        mock_model_cls.from_pretrained.assert_called_once()

        deepfake_detection.reset_model()
        m3, fe3, dev3 = deepfake_detection.get_model()
        self.assertEqual(mock_model_cls.from_pretrained.call_count, 2)

    # ── 14. Convenience entrypoint detect_deepfake_audio ─────────────────────

    @patch("app.modules.audio.deepfake_detection.AutoModelForAudioClassification")
    @patch("app.modules.audio.deepfake_detection.AutoFeatureExtractor")
    def test_convenience_detect_deepfake_audio(
        self, mock_fe_cls: MagicMock, mock_model_cls: MagicMock
    ) -> None:
        mock_model = _make_mock_model(torch.tensor([[3.0, -2.0]]))
        mock_model.to.return_value = mock_model
        mock_fe = _make_mock_fe()
        mock_model_cls.from_pretrained.return_value = mock_model
        mock_fe_cls.from_pretrained.return_value = mock_fe

        wav_path = self._get_temp_audio()
        out = deepfake_detection.detect_deepfake_audio(wav_path, threshold=0.7)

        self.assertEqual(out.status, DetectionStatus.SUCCESS)
        self.assertEqual(out.verdict, "synthetic_audio_signal_detected")

    # ── 15. Module 4 top-level run integration ───────────────────────────────

    @patch("app.modules.audio.deepfake_detection.AutoModelForAudioClassification")
    @patch("app.modules.audio.deepfake_detection.AutoFeatureExtractor")
    @patch("app.modules.audio.transcription.WhisperModel")
    def test_module4_top_level_run_both_components(
        self, mock_whisper_cls: MagicMock, mock_fe_cls: MagicMock, mock_model_cls: MagicMock
    ) -> None:
        # Mock Whisper
        mock_whisper = MagicMock()
        mock_whisper_cls.return_value = mock_whisper
        mock_whisper.transcribe.return_value = (
            iter([SimpleNamespace(id=0, start=0.0, end=1.0, text="Integrated test speech", no_speech_prob=0.01)]),
            SimpleNamespace(language="en", language_probability=0.99, duration=1.0),
        )

        # Mock Wav2Vec2
        mock_model = _make_mock_model(torch.tensor([[4.0, -1.0]]))
        mock_model.to.return_value = mock_model
        mock_fe = _make_mock_fe()
        mock_model_cls.from_pretrained.return_value = mock_model
        mock_fe_cls.from_pretrained.return_value = mock_fe

        wav_path = self._get_temp_audio()
        findings = _run_coro(module_run(AudioInput(audio_path=str(wav_path))))

        self.assertIsInstance(findings, AudioFindings)
        self.assertEqual(findings.transcript, "Integrated test speech")
        self.assertEqual(findings.synthetic_audio_signal, "synthetic_audio_signal_detected")
        self.assertIsNotNone(findings.detection_details)
        self.assertIsNotNone(findings.transcription_details)
        self.assertIsNone(findings.error)


if __name__ == "__main__":
    unittest.main()
