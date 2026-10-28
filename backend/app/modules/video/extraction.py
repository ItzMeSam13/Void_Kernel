"""
Module 3 — Video Intelligence: Stage 1 (dense snippet extraction) +
Stage 2 (MediaPipe FaceMesh face alignment & ROI crop).

Architecture references:
  - architecture.md Module 3 Pipeline steps 1–2
  - video_forensics_tech_spec.md Stages 1–2

Design decisions:
  - Three 30-frame windows at 10 / 50 / 90 % of video duration.
    Avoids the RAM blowup explicitly warned about in the spec.
  - MediaPipe FaceMesh with 468 landmarks.
  - Bounding box padded by 15% to capture jaw / neck blending seams.
  - Face crops are saved to /tmp/ to keep memory bounded; paths are
    returned in SnippetMeta so downstream tasks (Phase 2 spectral /
    rPPG streams) can load them independently without re-extracting.
  - No imports from any other module in app/modules/.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np

from app.modules.video.contracts import SnippetMeta

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SNIPPET_POSITIONS = (0.10, 0.50, 0.90)  # fractions of total duration
FRAMES_PER_SNIPPET = 30
FACE_BBOX_PAD = 0.15  # 15 % padding on all sides

# MediaPipe landmark indices that define a tight face bounding box.
# These are the outermost reliable landmarks (forehead top, chin, ears).
_OUTER_LANDMARK_INDICES = [
    10,   # forehead top
    152,  # chin bottom
    234,  # left ear region
    454,  # right ear region
    33,   # left eye outer corner
    263,  # right eye outer corner
]

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _open_capture(path: Path) -> cv2.VideoCapture:
    """Open a VideoCapture, raising ValueError if the file can't be read."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"cv2.VideoCapture could not open: {path}")
    return cap


def _snippet_start_frames(total_frames: int) -> list[int]:
    """
    Return the three start-frame indices for the dense snippets.
    Each window is FRAMES_PER_SNIPPET frames wide; clipped so the last
    frame of each snippet does not exceed total_frames - 1.
    """
    starts = []
    for pct in SNIPPET_POSITIONS:
        start = int(total_frames * pct)
        # Clamp so the full window fits inside the video.
        start = min(start, max(0, total_frames - FRAMES_PER_SNIPPET))
        starts.append(start)
    return starts


def _read_frames(cap: cv2.VideoCapture, start: int, count: int) -> list[np.ndarray]:
    """
    Seek to `start`, then read up to `count` frames.
    Returns a list (may be shorter than count if EOF reached early).
    """
    cap.set(cv2.CAP_PROP_POS_FRAMES, start)
    frames: list[np.ndarray] = []
    for _ in range(count):
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(frame)
    return frames


def _pad_bbox(x1: int, y1: int, x2: int, y2: int,
              img_w: int, img_h: int, pad: float = FACE_BBOX_PAD):
    """Apply fractional padding to a bounding box, clamped to image dimensions."""
    bw = x2 - x1
    bh = y2 - y1
    px = int(bw * pad)
    py = int(bh * pad)
    return (
        max(0, x1 - px),
        max(0, y1 - py),
        min(img_w, x2 + px),
        min(img_h, y2 + py),
    )


def _landmark_bbox(landmarks, img_w: int, img_h: int):
    """
    Derive a bounding box from the outer boundary MediaPipe landmarks.
    Returns (x1, y1, x2, y2) in pixel space, or None if landmarks is empty.
    """
    xs = [int(landmarks[i].x * img_w) for i in _OUTER_LANDMARK_INDICES
          if i < len(landmarks)]
    ys = [int(landmarks[i].y * img_h) for i in _OUTER_LANDMARK_INDICES
          if i < len(landmarks)]
    if not xs or not ys:
        return None
    return min(xs), min(ys), max(xs), max(ys)


# ---------------------------------------------------------------------------
# Public API — used only from run.py, no other module
# ---------------------------------------------------------------------------

def extract_snippets(video_path: Path, output_dir: Optional[Path] = None
                     ) -> list[SnippetMeta]:
    """
    Stage 1 + Stage 2: extract dense snippets and run FaceMesh on every frame.

    Parameters
    ----------
    video_path:
        Absolute path to the video file.
    output_dir:
        Directory where face crop images are saved.
        Defaults to a fresh subdirectory inside /tmp/.

    Returns
    -------
    list[SnippetMeta]
        One entry per snippet (up to 3). Each entry records start/end frames,
        face detection status, and paths to saved face-crop images.
    """
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="module3_snippets_"))
    output_dir.mkdir(parents=True, exist_ok=True)

    cap = _open_capture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames < 1:
        cap.release()
        raise ValueError(f"Video has no frames: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0  # fall back to 30 if unreadable
    logger.info(
        "Video: %s | frames=%d fps=%.2f", video_path.name, total_frames, fps
    )

    start_frames = _snippet_start_frames(total_frames)

    # Initialise MediaPipe FaceMesh once — reused across all snippets.
    face_mesh = mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=False,
        min_detection_confidence=0.5,
    )

    results: list[SnippetMeta] = []

    for snippet_idx, start_frame in enumerate(start_frames):
        end_frame = min(start_frame + FRAMES_PER_SNIPPET - 1, total_frames - 1)
        frames = _read_frames(cap, start_frame, FRAMES_PER_SNIPPET)

        if not frames:
            logger.warning("Snippet %d: no frames read (start=%d).", snippet_idx, start_frame)
            results.append(SnippetMeta(
                snippet_index=snippet_idx,
                start_frame=start_frame,
                end_frame=end_frame,
                position_pct=SNIPPET_POSITIONS[snippet_idx],
                face_detected=False,
            ))
            continue

        crop_paths: list[str] = []
        face_detected_in_snippet = False

        for frame_offset, frame_bgr in enumerate(frames):
            img_h, img_w = frame_bgr.shape[:2]
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

            mesh_result = face_mesh.process(frame_rgb)

            if not mesh_result.multi_face_landmarks:
                # No face in this frame — skip crop, continue to next frame.
                continue

            face_detected_in_snippet = True
            landmarks = mesh_result.multi_face_landmarks[0].landmark

            bbox = _landmark_bbox(landmarks, img_w, img_h)
            if bbox is None:
                continue

            x1, y1, x2, y2 = _pad_bbox(*bbox, img_w, img_h)
            face_crop = frame_bgr[y1:y2, x1:x2]

            if face_crop.size == 0:
                continue

            crop_name = f"snippet{snippet_idx}_frame{start_frame + frame_offset}.jpg"
            crop_path = output_dir / crop_name
            cv2.imwrite(str(crop_path), face_crop)
            crop_paths.append(str(crop_path))

        results.append(SnippetMeta(
            snippet_index=snippet_idx,
            start_frame=start_frame,
            end_frame=end_frame,
            position_pct=SNIPPET_POSITIONS[snippet_idx],
            face_detected=face_detected_in_snippet,
            face_crop_paths=crop_paths,
        ))

        logger.info(
            "Snippet %d (frames %d–%d): face_detected=%s crops=%d",
            snippet_idx, start_frame, end_frame,
            face_detected_in_snippet, len(crop_paths),
        )

    cap.release()
    face_mesh.close()

    return results
