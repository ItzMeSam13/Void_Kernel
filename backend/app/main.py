"""
main.py — FastAPI application entry point.

Mounts all API routers under /api/v1/:
  POST /api/v1/analyze              — upload + enqueue (Module 1 / Module 9)
  GET  /api/v1/results/{job_id}     — poll status / full structured result
  GET  /api/v1/results/{job_id}/report  — rendered explanation + evidence
  GET  /api/v1/reference/lookup     — Module 5 hash/pHash manual lookup
  GET  /api/v1/eval/{module}        — Module 8 eval report (analytics view)

architecture.md §Module 9 — Backend (FastAPI, already scaffolded in backend/app/main.py)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.analyze   import router as analyze_router
from app.api.v1.results   import router as results_router
from app.api.v1.reference import router as reference_router
from app.api.v1.eval      import router as eval_router

app = FastAPI(
    title       = "Void Kernel — Multimodal Misinformation Detector",
    description = (
        "PS-2 multimodal misinformation detection pipeline. "
        "Detects synthetic/manipulated media, fact-checks claims, "
        "and checks for historical out-of-context reuse."
    ),
    version     = "0.1.0",
    docs_url    = "/docs",
    redoc_url   = "/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],    # tighten in production
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── API v1 routes ─────────────────────────────────────────────────────────────
_PREFIX = "/api/v1"

app.include_router(analyze_router,   prefix=_PREFIX, tags=["Analysis"])
app.include_router(results_router,   prefix=_PREFIX, tags=["Results"])
app.include_router(reference_router, prefix=_PREFIX, tags=["Reference"])
app.include_router(eval_router,      prefix=_PREFIX, tags=["Evaluation"])


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def health():
    """Basic liveness check."""
    return {"status": "ok", "service": "void-kernel"}