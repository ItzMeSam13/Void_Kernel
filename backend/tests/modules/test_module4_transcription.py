"""
tests/modules/test_module4_transcription.py — Module 4 test runner hook.

Allows pytest / unittest test discovery from backend/tests to discover
and run Module 4's unit tests.
"""
from app.modules.audio.tests.test_transcription import TestAudioTranscription

__all__ = ["TestAudioTranscription"]

