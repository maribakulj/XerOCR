"""Résolution de la version de code estampillée dans les runs (couche 6).

Source unique : la version du paquet installé, sinon le fallback ``domain``
(``FALLBACK_VERSION``). Centralisé ici car la version entre dans la **provenance**
(`RunManifest`) — un concern d'``app`` — et était auparavant recopiée dans
plusieurs interfaces (CLI, web).
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from xerocr.domain._version_fallback import FALLBACK_VERSION


def resolve_code_version() -> str:
    """Version du paquet ``xerocr`` installé, ou le fallback ``domain``."""
    try:
        return version("xerocr")
    except PackageNotFoundError:  # pragma: no cover (paquet non installé)
        return FALLBACK_VERSION


__all__ = ["resolve_code_version"]
