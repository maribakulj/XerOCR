"""Erreurs de la couche évaluation."""

from __future__ import annotations

from xerocr.domain.errors import XerOCRError


class EvaluationError(XerOCRError):
    """Métrique inconnue, représentation non chargeable, entrée incohérente."""


__all__ = ["EvaluationError"]
