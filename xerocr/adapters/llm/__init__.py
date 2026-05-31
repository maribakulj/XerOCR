"""Adapters LLM (couche 5) — post-correction texte (mode ``text_only``)."""

from __future__ import annotations

from xerocr.adapters.llm.ollama import OllamaAdapter
from xerocr.adapters.llm.openai import OpenAIAdapter

__all__ = ["OllamaAdapter", "OpenAIAdapter"]
