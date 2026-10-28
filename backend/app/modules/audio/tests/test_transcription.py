"""
Unit tests for the speech transcription component (faster-whisper).

All model initialization and inference is mocked — these tests never download
model weights during execution or test collection.

To run a real-model smoke test, use ``run_transcribe.py`` instead.

Run with pytest (inside Docker or with pytest installed)::

    pytest app/modules/audio/tests/test_transcription.py -v

Or with Python's built-in unittest runner::

    python -m unittest app/modules/audio/tests/test_transcription.py
"""
from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pydantic import ValidationError

from app.modules.audio.contracts import (
    AudioInput,
    AudioFindings,
    AudioTranscriptionInput,
    AudioTranscriptionOutput,
    TranscriptSegment,
    TranscriptionStatus,
)
from app.modules.audio import transcription
from app.modules.audio import run as module_run


# ── Helpers ──────────────────────────────────────────────────────────────────

def _create_temp_wav(duration_sec: float = 1.0, sample_rate: int = 16000) -> Path:
    """Create a temporary valid silent WAV file for testing."""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = Path(tmp.name)
    tmp.close()

    with wave.open(str(tmp_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        num_frames = int(duration_sec * sample_rate)
        wf.writeframes(b"\x00\x00" * num_frames)

    return tmp_path


def _make_mock_segment(
    start: float,
    end: float,
    text: str,
    no_speech_prob: float = 0.01,
) -> SimpleNamespace:
    """Create a mock faster-whisper Segment namedtuple/dataclass."""
    return SimpleNamespace(
        id=0,
        seek=0,
        start=start,
        end=end,
        text=text,
        tokens=[1, 2, 3],
        avg_logprob=-0.2,
        compression_ratio=1.2,
        no_speech_prob=no_speech_prob,
        words=None,
        temperature=0.0,
    )


def _make_mock_info(
    language: str = "en",
    language_probability: float = 0.985,
    duration: float = 3.5,
) -> SimpleNamespace:
    """Create a mock faster-whisper TranscriptionInfo dataclass."""
    return SimpleNamespace(
        language=language,
        language_probability=language_probability,
        duration=duration,
        duration_after_vad=duration,
        all_language_probs=[(language, language_probability)],
        transcription_options={},
        vad_options={},
    )


def _run_coro(coro):
    """Run a coroutine without requiring an OS socket-based event loop."""
    try:
        coro.send(None)
    except StopIteration as exc:
        return exc.value
    raise RuntimeError("Coroutine did not finish synchronously")


# ── Test Suite ───────────────────────────────────────────────────────────────

class TestAudioTranscription(unittest.TestCase):
    """Test suite for faster-whisper transcription component."""

    def setUp(self) -> None:
        transcription.reset_model()
        self._temp_files: list[Path] = []

    def tearDown(self) -> None:
        transcription.reset_model()
        for p in self._temp_files:
            if p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass

    def _get_temp_wav(self) -> Path:
        p = _create_temp_wav()
        self._temp_files.append(p)
        return p

    # ── 1. Successful transcription with single segment ─────────────────────

    @patch("app.modules.audio.transcription.WhisperModel")
    def test_successful_transcription_single_segment(self, mock_whisper_cls: MagicMock) -> None:
        mock_model = MagicMock()
        mock_whisper_cls.return_value = mock_model

        mock_seg = _make_mock_segment(0.0, 2.5, "This is a single spoken sentence.")
        mock_info = _make_mock_info(language="en", language_probability=0.99, duration=2.5)

        # Transcribe returns (lazy generator, info)
        mock_model.transcribe.return_value = (iter([mock_seg]), mock_info)

        wav_path = self._get_temp_wav()
        inp = AudioTranscriptionInput(audio_path=str(wav_path))

        out = transcription.run(inp)

        self.assertEqual(out.status, TranscriptionStatus.SUCCESS)
        self.assertEqual(out.transcript, "This is a single spoken sentence.")
        self.assertEqual(len(out.segments), 1)
        self.assertEqual(out.segments[0].start, 0.0)
        self.assertEqual(out.segments[0].end, 2.5)
        self.assertEqual(out.segments[0].text, "This is a single spoken sentence.")
        self.assertEqual(out.language, "en")
        self.assertEqual(out.language_probability, 0.99)
        self.assertEqual(out.duration, 2.5)
        self.assertIsNone(out.error_message)

    # ── 2. Multiple segments & chronological ordering ───────────────────────

    @patch("app.modules.audio.transcription.WhisperModel")
    def test_successful_transcription_multiple_segments(self, mock_whisper_cls: MagicMock) -> None:
        mock_model = MagicMock()
        mock_whisper_cls.return_value = mock_model

        seg1 = _make_mock_segment(0.0, 1.8, "First statement.")
        seg2 = _make_mock_segment(2.0, 4.1, "Second statement with more words.")
        seg3 = _make_mock_segment(4.5, 6.0, "Concluding statement.")
        mock_info = _make_mock_info(language="en", language_probability=0.97, duration=6.0)

        mock_model.transcribe.return_value = (iter([seg1, seg2, seg3]), mock_info)

        wav_path = self._get_temp_wav()
        inp = AudioTranscriptionInput(audio_path=str(wav_path))

        out = transcription.run(inp)

        self.assertEqual(out.status, TranscriptionStatus.SUCCESS)
        self.assertEqual(
            out.transcript,
            "First statement. Second statement with more words. Concluding statement.",
        )
        self.assertEqual(len(out.segments), 3)
        self.assertEqual(out.segments[0].start, 0.0)
        self.assertEqual(out.segments[0].end, 1.8)
        self.assertEqual(out.segments[1].start, 2.0)
        self.assertEqual(out.segments[1].end, 4.1)
        self.assertEqual(out.segments[2].start, 4.5)
        self.assertEqual(out.segments[2].end, 6.0)

    # ── 3. Lazy segment generator is consumed completely ────────────────────

    @patch("app.modules.audio.transcription.WhisperModel")
    def test_lazy_generator_is_consumed(self, mock_whisper_cls: MagicMock) -> None:
        mock_model = MagicMock()
        mock_whisper_cls.return_value = mock_model

        consumed = []

        def generator_fn():
            for i in range(2):
                consumed.append(i)
                yield _make_mock_segment(float(i), float(i + 1), f"Segment {i}")

        mock_info = _make_mock_info()
        mock_model.transcribe.return_value = (generator_fn(), mock_info)

        wav_path = self._get_temp_wav()
        inp = AudioTranscriptionInput(audio_path=str(wav_path))

        out = transcription.run(inp)

        self.assertEqual(consumed, [0, 1], "Generator must be fully consumed and iterated")
        self.assertIsInstance(out.segments, list)
        self.assertEqual(len(out.segments), 2)

    # ── 4. Language metadata & automatic detection ──────────────────────────

    @patch("app.modules.audio.transcription.WhisperModel")
    def test_automatic_language_detection(self, mock_whisper_cls: MagicMock) -> None:
        mock_model = MagicMock()
        mock_whisper_cls.return_value = mock_model

        mock_seg = _make_mock_segment(0.0, 2.0, "Hola mundo")
        mock_info = _make_mock_info(language="es", language_probability=0.9654, duration=2.0)
        mock_model.transcribe.return_value = (iter([mock_seg]), mock_info)

        wav_path = self._get_temp_wav()
        inp = AudioTranscriptionInput(audio_path=str(wav_path), language=None)

        out = transcription.run(inp)

        self.assertEqual(out.status, TranscriptionStatus.SUCCESS)
        self.assertEqual(out.language, "es")
        self.assertEqual(out.language_probability, 0.9654)
        # Verify language=None was passed to transcribe() for auto-detection
        mock_model.transcribe.assert_called_once()
        _, kwargs = mock_model.transcribe.call_args
        self.assertIsNone(kwargs["language"])

    # ── 5. Explicit language hint handling ──────────────────────────────────

    @patch("app.modules.audio.transcription.WhisperModel")
    def test_explicit_language_hint_forwarded(self, mock_whisper_cls: MagicMock) -> None:
        mock_model = MagicMock()
        mock_whisper_cls.return_value = mock_model

        mock_seg = _make_mock_segment(0.0, 1.5, "Bonjour le monde")
        mock_info = _make_mock_info(language="fr", language_probability=0.99, duration=1.5)
        mock_model.transcribe.return_value = (iter([mock_seg]), mock_info)

        wav_path = self._get_temp_wav()
        inp = AudioTranscriptionInput(audio_path=str(wav_path), language="fr")

        out = transcription.run(inp)

        self.assertEqual(out.status, TranscriptionStatus.SUCCESS)
        self.assertEqual(out.language, "fr")
        _, kwargs = mock_model.transcribe.call_args
        self.assertEqual(kwargs["language"], "fr")

    # ── 6. Valid audio with no detected speech ──────────────────────────────

    @patch("app.modules.audio.transcription.WhisperModel")
    def test_valid_audio_no_speech_detected(self, mock_whisper_cls: MagicMock) -> None:
        mock_model = MagicMock()
        mock_whisper_cls.return_value = mock_model

        # Model returns empty generator (silence)
        mock_info = _make_mock_info(language="en", language_probability=0.5, duration=5.0)
        mock_model.transcribe.return_value = (iter([]), mock_info)

        wav_path = self._get_temp_wav()
        inp = AudioTranscriptionInput(audio_path=str(wav_path))

        out = transcription.run(inp)

        self.assertEqual(out.status, TranscriptionStatus.NO_SPEECH_DETECTED)
        self.assertEqual(out.transcript, "")
        self.assertEqual(out.segments, [])
        self.assertEqual(out.duration, 5.0)
        self.assertIsNone(out.error_message)

    @patch("app.modules.audio.transcription.WhisperModel")
    def test_valid_audio_whitespace_only_segments_treated_as_no_speech(self, mock_whisper_cls: MagicMock) -> None:
        mock_model = MagicMock()
        mock_whisper_cls.return_value = mock_model

        # Model returns whitespace/noise segments
        seg = _make_mock_segment(0.0, 1.0, "   ", no_speech_prob=0.98)
        mock_info = _make_mock_info(duration=1.0)
        mock_model.transcribe.return_value = (iter([seg]), mock_info)

        wav_path = self._get_temp_wav()
        inp = AudioTranscriptionInput(audio_path=str(wav_path))

        out = transcription.run(inp)

        self.assertEqual(out.status, TranscriptionStatus.NO_SPEECH_DETECTED)
        self.assertEqual(out.transcript, "")

    # ── 7. Missing audio file or invalid path ────────────────────────────────

    def test_missing_audio_file_returns_error(self) -> None:
        non_existent = Path(tempfile.gettempdir()) / "non_existent_audio_xyz123.wav"
        if non_existent.exists():
            non_existent.unlink()

        inp = AudioTranscriptionInput(audio_path=str(non_existent))
        out = transcription.run(inp)

        self.assertEqual(out.status, TranscriptionStatus.ERROR)
        self.assertIn("Audio file not found", out.error_message)
        self.assertEqual(out.transcript, "")

    def test_empty_audio_file_returns_error(self) -> None:
        empty_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        empty_path = Path(empty_file.name)
        empty_file.close()
        self._temp_files.append(empty_path)

        inp = AudioTranscriptionInput(audio_path=str(empty_path))
        out = transcription.run(inp)

        self.assertEqual(out.status, TranscriptionStatus.ERROR)
        self.assertIn("empty", out.error_message.lower())

    def test_directory_instead_of_file_returns_error(self) -> None:
        tmp_dir = tempfile.mkdtemp()
        inp = AudioTranscriptionInput(audio_path=tmp_dir)
        out = transcription.run(inp)

        self.assertEqual(out.status, TranscriptionStatus.ERROR)
        self.assertIn("not a file", out.error_message.lower())
        os.rmdir(tmp_dir)

    def test_empty_string_path_raises_pydantic_validation(self) -> None:
        with self.assertRaises(ValidationError):
            AudioTranscriptionInput(audio_path="")

    # ── 8. Audio decoding or inference failures ──────────────────────────────

    @patch("app.modules.audio.transcription.WhisperModel")
    def test_audio_decoding_or_inference_failure(self, mock_whisper_cls: MagicMock) -> None:
        mock_model = MagicMock()
        mock_whisper_cls.return_value = mock_model

        mock_model.transcribe.side_effect = RuntimeError("Failed to decode audio stream: invalid data")

        wav_path = self._get_temp_wav()
        inp = AudioTranscriptionInput(audio_path=str(wav_path))

        out = transcription.run(inp)

        self.assertEqual(out.status, TranscriptionStatus.ERROR)
        self.assertIn("failed", out.error_message.lower())
        self.assertIn("invalid data", out.error_message.lower())

    # ── 9. Model loading failure ────────────────────────────────────────────

    @patch("app.modules.audio.transcription.WhisperModel")
    def test_model_loading_failure(self, mock_whisper_cls: MagicMock) -> None:
        mock_whisper_cls.side_effect = OSError("Out of memory while allocating model weights")

        wav_path = self._get_temp_wav()
        inp = AudioTranscriptionInput(audio_path=str(wav_path))

        out = transcription.run(inp)

        self.assertEqual(out.status, TranscriptionStatus.ERROR)
        self.assertIn("Model initialization failed", out.error_message)

    # ── 10. Output contract compliance & timestamp validation ───────────────

    def test_transcript_segment_validation(self) -> None:
        # Valid segment
        seg = TranscriptSegment(start=1.0, end=2.5, text="Valid segment")
        self.assertEqual(seg.start, 1.0)
        self.assertEqual(seg.end, 2.5)

        # Negative timestamp
        with self.assertRaises(ValidationError):
            TranscriptSegment(start=-1.0, end=2.0, text="Negative start")

        # End before start
        with self.assertRaises(ValidationError):
            TranscriptSegment(start=5.0, end=3.0, text="Inverted timestamps")

    # ── 11. Device & compute type resolution ─────────────────────────────────

    def test_device_and_compute_type_resolution_cpu_safety(self) -> None:
        # When device is cpu, float16 should be replaced with int8 to prevent CTranslate2 crashes
        dev, compute = transcription._resolve_device_and_compute_type("cpu", "float16")
        self.assertEqual(dev, "cpu")
        self.assertEqual(compute, "int8")

        dev2, compute2 = transcription._resolve_device_and_compute_type("cpu", "default")
        self.assertEqual(dev2, "cpu")
        self.assertEqual(compute2, "int8")

    # ── 12. Singleton reuse and reset ────────────────────────────────────────

    @patch("app.modules.audio.transcription.WhisperModel")
    def test_model_singleton_reuse(self, mock_whisper_cls: MagicMock) -> None:
        mock_instance = MagicMock()
        mock_whisper_cls.return_value = mock_instance

        # Call get_model twice with same params
        m1 = transcription.get_model(model_size="small", device="cpu", compute_type="int8")
        m2 = transcription.get_model(model_size="small", device="cpu", compute_type="int8")

        self.assertIs(m1, m2)
        mock_whisper_cls.assert_called_once()

        # Reset model
        transcription.reset_model()
        m3 = transcription.get_model(model_size="small", device="cpu", compute_type="int8")
        self.assertEqual(mock_whisper_cls.call_count, 2)

    # ── 13. Convenience wrapper transcribe_audio ────────────────────────────

    @patch("app.modules.audio.transcription.WhisperModel")
    def test_convenience_transcribe_audio(self, mock_whisper_cls: MagicMock) -> None:
        mock_model = MagicMock()
        mock_whisper_cls.return_value = mock_model
        mock_model.transcribe.return_value = (
            iter([_make_mock_segment(0.0, 1.0, "Testing convenience")]),
            _make_mock_info(),
        )

        wav_path = self._get_temp_wav()
        out = transcription.transcribe_audio(wav_path, language="en", model_size="small")

        self.assertEqual(out.status, TranscriptionStatus.SUCCESS)
        self.assertEqual(out.transcript, "Testing convenience")

    # ── 14. Top-level Module 4 run entrypoint ───────────────────────────────

    @patch("app.modules.audio.transcription.WhisperModel")
    def test_module4_async_run_entrypoint(self, mock_whisper_cls: MagicMock) -> None:
        mock_model = MagicMock()
        mock_whisper_cls.return_value = mock_model
        mock_model.transcribe.return_value = (
            iter([_make_mock_segment(0.0, 2.0, "Module 4 full transcript")]),
            _make_mock_info(),
        )

        wav_path = self._get_temp_wav()
        findings = _run_coro(module_run(AudioInput(audio_path=str(wav_path))))

        self.assertIsInstance(findings, AudioFindings)
        self.assertEqual(findings.transcript, "Module 4 full transcript")
        self.assertIsNotNone(findings.transcription_details)
        self.assertEqual(findings.transcription_details.status, TranscriptionStatus.SUCCESS)
        self.assertIsNone(findings.error)

    # ── 15. Top-level Module 4 run handles missing audio_path ───────────────

    def test_module4_async_run_missing_path(self) -> None:
        findings = _run_coro(module_run(AudioInput(audio_path=None)))
        self.assertIsInstance(findings, AudioFindings)
        self.assertIn("No audio_path", findings.error)


if __name__ == "__main__":
    unittest.main()
