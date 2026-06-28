"""Adapters LLM/VLM (couche 5) — post-correction texte/image + transcription VLM.

Modes par adapter (``PipelineMode``) : ``text_only`` (tous), ``text_and_image``
et ``zero_shot`` (openai, mistral, anthropic — vision). ``ollama`` reste
``text_only`` (socle local minimal).
"""

from __future__ import annotations

from cinoc.adapters.llm.anthropic import AnthropicAdapter
from cinoc.adapters.llm.mistral import MistralAdapter
from cinoc.adapters.llm.ollama import OllamaAdapter
from cinoc.adapters.llm.openai import OpenAIAdapter

__all__ = ["AnthropicAdapter", "MistralAdapter", "OllamaAdapter", "OpenAIAdapter"]
