"""Erreurs de la couche évaluation."""

from __future__ import annotations

from cinoc.domain.errors import CinocError


class EvaluationError(CinocError):
    """Métrique inconnue, représentation non chargeable, entrée incohérente."""


__all__ = ["EvaluationError"]
