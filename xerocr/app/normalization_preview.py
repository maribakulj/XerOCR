"""Aperçu de normalisation (couche 6) — applique un profil à un échantillon.

Sert le formulaire (``POST /api/normalization/preview``) : résout soit un profil
**nommé** (socle couche 2), soit une **config YAML custom** (parsée à la volée,
**jamais persistée**), et renvoie l'échantillon normalisé. La config custom est
validée par Pydantic (clés inconnues interdites) ; toute config/erreur YAML remonte
une ``NormalizationPreviewError`` typée (que la couche 8 traduit en ``422``).
"""

from __future__ import annotations

import yaml
from pydantic import ValidationError

from xerocr.domain.errors import XerOCRError
from xerocr.formats.text import NORMALIZATION_PROFILES
from xerocr.formats.text.normalization import NormalizationProfile


class NormalizationPreviewError(XerOCRError):
    """Profil nommé inconnu, ou config YAML custom invalide."""


def _resolve(profile: str | None, config: str | None) -> NormalizationProfile:
    """Config custom (prioritaire) > profil nommé > erreur (jamais un défaut muet)."""
    if config:
        try:
            return NormalizationProfile.from_yaml_text(config)
        except (yaml.YAMLError, ValidationError, ValueError) as exc:
            raise NormalizationPreviewError(f"config invalide : {exc}") from exc
    if profile:
        resolved = NORMALIZATION_PROFILES.get(profile)
        if resolved is None:
            raise NormalizationPreviewError(f"profil inconnu : {profile!r}.")
        return resolved
    raise NormalizationPreviewError("aperçu : un profil OU une config est requis.")


def preview_normalization(
    sample: str, *, profile: str | None = None, config: str | None = None
) -> str:
    """Renvoie ``sample`` normalisé par le profil résolu (nommé ou custom)."""
    return _resolve(profile, config).normalize(sample)


__all__ = ["NormalizationPreviewError", "preview_normalization"]
