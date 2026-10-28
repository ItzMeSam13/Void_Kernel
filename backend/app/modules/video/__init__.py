"""
modules/video/__init__.py — Module 3 public entrypoint (stub).

Person 2 implements the tri-stream deepfake engine here.
"""
from __future__ import annotations

from app.modules.video.contracts import VideoInput, VideoFindings


async def run(inp: VideoInput) -> VideoFindings:
    """
    STUB — Person 2 replaces this body.

    Full implementation (video_forensics_tech_spec.md):
      1. FFmpeg/OpenCV dense snippet extraction (3 × 30-frame windows).
      2. MediaPipe FaceMesh alignment.
      3. Spectral stream — DCT, split into spectral_artifact_score + signal_integrity_score.
      4. rPPG stream — forehead green channel, bandpass 0.7–2.5 Hz.
      5. Spatial ViT + attention rollout + landmark-to-text mapping.
      6. Weighted-peak tri-stream fusion.
      7. Module 2 analyze_image() on sampled frames (per-frame, timestamped).
    """
    return VideoFindings(
        error="Module 3 (video) not yet implemented — stub."
    )
