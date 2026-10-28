"""
modules/image/contracts.py — Module 2 public contracts (Person 3 owns this).

ImageInput / ImageFindings form the ONLY interface surface of Module 2.
The orchestrator calls run(ImageInput) → ImageFindings.
No other module imports from here except state.py (which re-exports ImageFindings).

Stub: replace with the real models once Person 3 freezes the contract.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class ImageInput(BaseModel):
    """Input to Module 2's analyze_image() entrypoint."""
    image_path:  Optional[str] = Field(None, description="Local path to the image file.")
    image_bytes: Optional[bytes] = Field(None, description="Raw image bytes (alternative to path).")
    claim_text:  Optional[str]  = Field(None, description="User-supplied caption or claim text.")


class ImageFindings(BaseModel):
    """
    Output of Module 2's analyze_image() entrypoint.
    Matches the stub in orchestrator/state.py — keep in sync.
    """
    caption:                  Optional[str]   = None
    clip_similarity_score:    Optional[float] = Field(None, ge=0.0, le=1.0,
        description="CLIP claim-image semantic similarity (0=no match, 1=perfect match).")
    ocr_text:                 Optional[str]   = None
    smaug_ai_score:           Optional[float] = Field(None, ge=0.0, le=1.0,
        description="Probability image is AI-generated (Smaug detector).")
    manipulation_detected:    Optional[bool]  = None
    manipulation_confidence:  Optional[float] = Field(None, ge=0.0, le=1.0)
    manipulation_heatmap_path: Optional[str]  = None
    error:                    Optional[str]   = None
