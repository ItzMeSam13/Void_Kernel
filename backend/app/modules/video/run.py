"""
Module 3 — Video Intelligence: public entrypoint.

Architecture rule (§6):
  - This is the ONLY public surface of the module.
  - Signature: run(input: VideoInput) -> VideoFindings
  - Zero knowledge of orchestration frameworks (LangGraph / ARQ / FastAPI).
  - Callable standalone: python -c "
        from pathlib import Path
        from app.modules.video.run import run
        from app.modules.video.contracts import VideoInput
        result = run(VideoInput(video_path=Path('my_video.mp4')))
        print(result.model_dump_json(indent=2))
    "

Phase coverage:
  Phase 1 (NOW):  snippet extraction + FaceMesh → extraction_meta, face_roi_count
  Phase 2 (next): spectral, rPPG, per-frame Module 2 calls → forensic_streams.*,
                  frame_analyses, flagged_segments_sec, concrete_evidence
  Phase 3 (later): spatial ViT + attention rollout, weighted-peak fusion → verdict,
                   confidence_score, saliency_heatmap_path
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.modules.video.contracts import VideoFindings, VideoInput
from app.modules.video.extraction import extract_snippets

logger = logging.getLogger(__name__)


def run(input: VideoInput) -> VideoFindings:
    """
    Analyse a video file for deepfake signals.

    Phase 1 populates:
      - findings.extraction_meta  (per-snippet frame range + face-crop paths)
      - findings.face_roi_count   (total face crops across all snippets)
      - findings.errors           (non-fatal issues, e.g. no face detected)

    All other fields (verdict, confidence_score, forensic_streams.*,
    concrete_evidence, saliency_heatmap_path, frame_analyses) default to
    NOT_ASSESSED / None / [] as declared in VideoFindings — ready for
    Phase 2/3 to fill in without changing the contract.

    Parameters
    ----------
    input : VideoInput
        VideoInput.video_path must be an existing file.
        VideoInput.claim_text is passed through for Phase 2 per-frame calls.

    Returns
    -------
    VideoFindings
        Fully typed output consumed by Module 7 (fusion) and Module 1 (GraphState).
    """
    video_path = Path(input.video_path)

    if not video_path.exists():
        logger.error("Video file not found: %s", video_path)
        return VideoFindings(
            errors=[f"Video file not found: {video_path}"]
        )

    errors: list[str] = []

    # ------------------------------------------------------------------
    # Stage 1 + Stage 2: dense snippet extraction + MediaPipe FaceMesh
    # ------------------------------------------------------------------
    try:
        snippet_metas = extract_snippets(video_path)
    except Exception as exc:
        logger.exception("Snippet extraction failed for %s", video_path)
        return VideoFindings(
            errors=[f"Snippet extraction failed: {exc}"]
        )

    # Count total face crops across all snippets.
    face_roi_count = sum(len(s.face_crop_paths) for s in snippet_metas)

    # Warn (non-fatally) if no face was found in any snippet — a face-swap
    # deepfake engine can't run without a face, so Phase 2 will propagate
    # NOT_ASSESSED for all streams. This is "fail honest, not silent"
    # (Guiding Principle 4).
    if face_roi_count == 0:
        msg = (
            "No face detected in any snippet. "
            "Tri-stream forensic analysis (Phase 2/3) will output NOT_ASSESSED. "
            "Consider: non-face video, very dark/blurry footage, or sub-1s clip."
        )
        logger.warning(msg)
        errors.append(msg)

    logger.info(
        "Phase 1 complete | snippets=%d face_rois=%d errors=%d",
        len(snippet_metas), face_roi_count, len(errors),
    )

    return VideoFindings(
        extraction_meta=snippet_metas,
        face_roi_count=face_roi_count,
        errors=errors,
        # All Phase 2/3 fields deliberately left at their defaults:
        #   verdict = NOT_ASSESSED
        #   confidence_score = None
        #   forensic_streams = ForensicStreams()  (all sub-fields = None / NOT_ASSESSED)
        #   flagged_segments_sec = []
        #   concrete_evidence = []
        #   saliency_heatmap_path = None
        #   frame_analyses = []
    )
