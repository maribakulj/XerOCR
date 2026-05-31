"""Registre + factory de modules (couche 6).

Résout un ``adapter_name`` (convention ``<kind>:<label>``) vers une instance de
``Module`` (couche 4) en appelant un **builder** enregistré pour le ``kind``.
C'est le **seul** point d'extension du produit : en T1 le socle est enregistré
**en dur** (``register_default_modules``) ; la **découverte de plugins tiers**
(entry-points ``xerocr.modules``) s'y branchera en T6 — même résolution
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

    return OpenAIAdapter(label=label, model=str(kwargs.get("model", "gpt-4o-mini")))


def register_default_modules(registry: ModuleRegistry) -> None:
    """Enregistre le socle (starter pack). Aucun effet de bord à l'import."""
    registry.register_builder("precomputed", _build_precomputed)
    registry.register_builder("tesseract", _build_tesseract)
    registry.register_builder("openai", _build_openai)


__all__ = [
    "ModuleBuilder",
    "ModuleRegistry",
    "ModuleResolutionError",
    "register_default_modules",
]
