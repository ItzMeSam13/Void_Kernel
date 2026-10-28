"""
tests/modules/test_module4_deepfake.py — Module 4 deepfake test runner hook.

Allows pytest / unittest test discovery from backend/tests to discover
and run Module 4's Wav2Vec2 synthetic-audio unit tests.
"""
from app.modules.audio.tests.test_deepfake_detection import TestDeepfakeAudioDetection

__all__ = ["TestDeepfakeAudioDetection"]

