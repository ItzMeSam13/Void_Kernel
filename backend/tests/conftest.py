"""
Shared test fixtures.

llm_client._generate_gemini() raises EnvironmentError before ever touching
the `generate` mock if GOOGLE_API_KEY/GEMINI_API_KEY is unset — even in
tests that patch `generate` itself, since real code only reaches that
branch when FACTCHECK_LLM_BACKEND=gemini. The dummy key below only fills
the gap when nothing real is already loaded from .env, so it never
clobbers a real key you're using to test the live Gemini backend.

Deliberately does NOT set TAVILY_API_KEY / GOOGLE_FACT_CHECK_API_KEY /
SUPABASE_* — tests relying on those being absent (fail-honest paths)
must keep seeing them absent unless you've put real ones in .env.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load backend/.env (if present) before any test runs, so real keys you
# drop in there (see .env.example) are picked up without manual exporting.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@pytest.fixture(autouse=True)
def _dummy_gemini_key(monkeypatch):
    if not (os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")):
        monkeypatch.setenv("GOOGLE_API_KEY", "test-dummy-key")
