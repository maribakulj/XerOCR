"""Registre + factory de modules (couche 6).

Résout un ``adapter_name`` (convention ``<kind>:<label>``) vers une instance de
``Module`` (couche 4) en appelant un **builder** enregistré pour le ``kind``.
C'est le **seul** point d'extension du produit : le socle est enregistré
**en dur** (``register_default_modules``) ; la **découverte de plugins tiers**
(entry-points ``xerocr.modules``, cf. ``app.modules.discovery``) — même résolution
``name → Module``, source différente.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from xerocr.domain.errors import XerOCRError
from xerocr.pipeline.protocols import Module, ParamValue

#: Construit une instance de module depuis ses kwargs de construction.
ModuleBuilder = Callable[[Mapping[str, ParamValue]], Module]


class ModuleResolutionError(XerOCRError):
    """``kind`` inconnu, kwargs invalides, ou nom construit incohérent."""


class ModuleRegistry:
    """Associe un ``kind`` à un builder, et construit les modules d'un run."""

    def __init__(self) -> None:
        self._builders: dict[str, ModuleBuilder] = {}

    def register_builder(self, kind: str, builder: ModuleBuilder) -> None:
        """Enregistre (ou remplace) le builder d'un ``kind``. Idempotent."""
        self._builders[kind] = builder

    def kinds(self) -> tuple[str, ...]:
        return tuple(sorted(self._builders))

    def build(self, adapter_name: str, kwargs: Mapping[str, ParamValue]) -> Module:
        """Construit le module ``adapter_name`` (``kind`` = avant le ``:``)."""
        kind = adapter_name.split(":", 1)[0]
        builder = self._builders.get(kind)
        if builder is None:
            raise ModuleResolutionError(
                f"aucun builder pour le kind {kind!r} (module {adapter_name!r})."
            )
        module = builder(kwargs)
        if module.name != adapter_name:
            raise ModuleResolutionError(
                f"module construit {module.name!r} ≠ nom déclaré "
                f"{adapter_name!r} (kwargs incohérents ?)."
            )
        return module


def _build_precomputed(kwargs: Mapping[str, ParamValue]) -> Module:
    label = kwargs.get("source_label")
    if not isinstance(label, str):
        raise ModuleResolutionError(
            "precomputed : 'source_label' (str) requis dans adapter_kwargs."
        )
    from xerocr.adapters.ocr.precomputed import PrecomputedTextAdapter

    return PrecomputedTextAdapter(source_label=label)


def _build_tesseract(kwargs: Mapping[str, ParamValue]) -> Module:
    label = kwargs.get("label")
    if not isinstance(label, str):
        raise ModuleResolutionError(
            "tesseract : 'label' (str) requis dans adapter_kwargs."
        )
    from xerocr.adapters.ocr.tesseract import TesseractAdapter

    return TesseractAdapter(
        label=label,
        lang=str(kwargs.get("lang", "fra")),
        psm=int(kwargs.get("psm", 6)),
        oem=int(kwargs.get("oem", 3)),
    )


def _build_openai(kwargs: Mapping[str, ParamValue]) -> Module:
    label = kwargs.get("label")
    if not isinstance(label, str):
        raise ModuleResolutionError(
            "openai : 'label' (str) requis dans adapter_kwargs."
        )
    from xerocr.adapters.llm.openai import OpenAIAdapter

    prompt = kwargs.get("prompt")
    return OpenAIAdapter(
        label=label,
        model=str(kwargs.get("model", "gpt-4o-mini")),
        role=str(kwargs.get("role", "text_only")),
        prompt=prompt if isinstance(prompt, str) else None,
    )


def _build_ollama(kwargs: Mapping[str, ParamValue]) -> Module:
    label = kwargs.get("label")
    if not isinstance(label, str):
        raise ModuleResolutionError(
            "ollama : 'label' (str) requis dans adapter_kwargs."
        )
    from xerocr.adapters.llm.ollama import OllamaAdapter

    prompt = kwargs.get("prompt")
    extra = {"prompt": prompt} if isinstance(prompt, str) else {}
    return OllamaAdapter(
        label=label,
        model=str(kwargs.get("model", "llama3")),
        host=str(kwargs.get("host", "http://localhost:11434")),
        **extra,
    )


def _build_mistral(kwargs: Mapping[str, ParamValue]) -> Module:
    label = kwargs.get("label")
    if not isinstance(label, str):
        raise ModuleResolutionError(
            "mistral : 'label' (str) requis dans adapter_kwargs."
        )
    from xerocr.adapters.llm.mistral import MistralAdapter

    prompt = kwargs.get("prompt")
    return MistralAdapter(
        label=label,
        model=str(kwargs.get("model", "mistral-small-latest")),
        role=str(kwargs.get("role", "text_only")),
        prompt=prompt if isinstance(prompt, str) else None,
    )


def _build_anthropic(kwargs: Mapping[str, ParamValue]) -> Module:
    label = kwargs.get("label")
    if not isinstance(label, str):
        raise ModuleResolutionError(
            "anthropic : 'label' (str) requis dans adapter_kwargs."
        )
    from xerocr.adapters.llm.anthropic import AnthropicAdapter

    prompt = kwargs.get("prompt")
    return AnthropicAdapter(
        label=label,
        model=str(kwargs.get("model", "claude-haiku-4-5-20251001")),
        role=str(kwargs.get("role", "text_only")),
        prompt=prompt if isinstance(prompt, str) else None,
    )


def _build_precomputed_layout(kwargs: Mapping[str, ParamValue]) -> Module:
    from xerocr.adapters.layout.precomputed import PrecomputedLayoutSource

    return PrecomputedLayoutSource()


def _build_pp_doclayout(kwargs: Mapping[str, ParamValue]) -> Module:
    from xerocr.adapters.layout.pp_doclayout import PPDocLayoutSegmenter

    return PPDocLayoutSegmenter()

def _build_precomputed_region(kwargs: Mapping[str, ParamValue]) -> Module:
    label = kwargs.get("source_label")
    if not isinstance(label, str):
        raise ModuleResolutionError(
            "precomputed_region : 'source_label' (str) requis dans adapter_kwargs."
        )
    from xerocr.adapters.layout.precomputed import PrecomputedRegionRecognizer

    return PrecomputedRegionRecognizer(source_label=label)


def _build_alto_assembler(kwargs: Mapping[str, ParamValue]) -> Module:
    from xerocr.adapters.layout.assembler import AltoAssembler

    return AltoAssembler()


def register_default_modules(registry: ModuleRegistry) -> None:
    """Enregistre le socle (starter pack). Aucun effet de bord à l'import."""
    registry.register_builder("precomputed", _build_precomputed)
    registry.register_builder("tesseract", _build_tesseract)
    registry.register_builder("openai", _build_openai)
    registry.register_builder("ollama", _build_ollama)
    registry.register_builder("mistral", _build_mistral)
    registry.register_builder("anthropic", _build_anthropic)
    registry.register_builder("precomputed_layout", _build_precomputed_layout)
    registry.register_builder("pp_doclayout", _build_pp_doclayout)
    registry.register_builder("precomputed_region", _build_precomputed_region)
    registry.register_builder("alto_assembler", _build_alto_assembler)


__all__ = [
    "ModuleBuilder",
    "ModuleRegistry",
    "ModuleResolutionError",
    "register_default_modules",
]
