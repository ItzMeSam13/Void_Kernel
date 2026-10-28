"""
Module 6 — llm_client.py
Pluggable single-call LLM backend shared by claim_splitter.py and
evidence_judge.py.

architecture.md specifies Gemini for both calls (claim splitting, evidence
judging). Swapped to a local Ollama model via LangChain for now — no
Gemini API key is available yet, and this keeps Module 6 fully callable
offline during development. Switch back to Gemini later by setting
FACTCHECK_LLM_BACKEND=gemini; call sites (claim_splitter.py,
evidence_judge.py) don't change either way.

Isolation rule (§6): this file only knows plain strings in, plain string
out. No knowledge of claims, evidence, or any other module.
"""
from __future__ import annotations

import os
from functools import lru_cache


@lru_cache(maxsize=1)
def _get_ollama_llm():
    """Lazily build the LangChain Ollama chat client once per process."""
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=os.environ.get("OLLAMA_MODEL", "phi3:mini"),
        base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0,
    )


def _generate_ollama(system_instruction: str, user_prompt: str) -> str:
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = _get_ollama_llm()
    response = llm.invoke(
        [SystemMessage(content=system_instruction), HumanMessage(content=user_prompt)]
    )
    return response.content


def _generate_gemini(system_instruction: str, user_prompt: str) -> str:
    import google.generativeai as genai

    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_API_KEY or GEMINI_API_KEY environment variable is not set.")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
        system_instruction=system_instruction,
    )
    response = model.generate_content(user_prompt)
    return response.text


def generate(system_instruction: str, user_prompt: str) -> str:
    """
    Single text-in/text-out LLM call. Backend selected by
    FACTCHECK_LLM_BACKEND env var: 'ollama' (default, local/offline) or
    'gemini' (architecture.md's eventual default, needs an API key).

    Raises on failure — callers already wrap this in their own
    try/except fallback paths (Guiding Principle 4: fail honest).
    """
    backend = os.environ.get("FACTCHECK_LLM_BACKEND", "ollama").lower()
    if backend == "gemini":
        return _generate_gemini(system_instruction, user_prompt)
    return _generate_ollama(system_instruction, user_prompt)
