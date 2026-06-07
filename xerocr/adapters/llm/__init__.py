"""Adapters LLM/VLM (couche 5) — post-correction texte/image + transcription VLM.

Modes par adapter (``PipelineMode``) : ``text_only`` (tous), ``text_and_image``
et ``zero_shot`` (openai, mistral, anthropic — vision). ``ollama`` reste
``text_only`` (socle local minimal).
"""

from __future__ import annotations

from xerocr.adapters.llm.anthropic import AnthropicAdapter
from xerocr.adapters.llm.mistral import MistralAdapter
from xerocr.adapters.llm.ollama import OllamaAdapter
from xerocr.adapters.llm.openai import OpenAIAdapter

__all__ = ["AnthropicAdapter", "MistralAdapter", "OllamaAdapter", "OpenAIAdapter"]
