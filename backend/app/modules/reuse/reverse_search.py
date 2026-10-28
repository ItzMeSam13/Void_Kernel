"""
Module 5 — reverse_search.py
Optional SerpApi Google Lens reverse-image search.

Architecture §Module 5: "gate behind a feature flag since it's a paid
external call."  This module is ONLY invoked when
ENABLE_REVERSE_SEARCH=true in env.  Phase 4 stretch.

The function returns a plain list[dict] so that ReuseFindings can store
raw API hits without imposing a schema on a paid external service that
may change its response shape.
"""
from __future__ import annotations

import os
from typing import Optional

import requests


SERPAPI_ENDPOINT = "https://serpapi.com/search"
_TIMEOUT_SECONDS = 10


def reverse_image_search(
    image_url: Optional[str] = None,
    image_path: Optional[str] = None,
) -> list[dict]:
    """
    Submit an image to SerpApi's Google Lens endpoint and return raw hits.

    Exactly one of `image_url` or `image_path` must be set.
    Returns an empty list (not an error) if ENABLE_REVERSE_SEARCH is not
    set to 'true' — callers don't need to check the flag themselves.

    Guiding Principle 4 (fail honest): on any exception the function
    returns an empty list and logs a warning rather than raising, so a
    network failure doesn't break the whole pipeline.
    """
    if os.environ.get("ENABLE_REVERSE_SEARCH", "false").lower() != "true":
        return []

    api_key = os.environ.get("SERPAPI_KEY", "")
    if not api_key:
        return []

    params: dict = {
        "engine": "google_lens",
        "api_key": api_key,
    }
    files = None
    if image_url:
        params["url"] = image_url
    elif image_path:
        files = {"image": open(image_path, "rb")}
    else:
        return []

    try:
        resp = requests.post(
            SERPAPI_ENDPOINT,
            params=params,
            files=files,
            timeout=_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        # SerpApi returns visual_matches under "visual_matches" key
        return data.get("visual_matches", [])
    except Exception as exc:  # noqa: BLE001
        import warnings
        warnings.warn(f"[Module5/reverse_search] SerpApi call failed: {exc}")
        return []
    finally:
        if files:
            for fh in files.values():
                fh.close()
