"""Entrées/sorties JSON d'un ``RunResult`` (couche 6).

Sérialisation déterministe (Pydantic) pour **sauver** un run et le **comparer**
plus tard (``xerocr compare``). Aucun calcul ici — juste le round-trip.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from xerocr.domain.errors import XerOCRError
from xerocr.evaluation.result import RunResult


class RunResultError(XerOCRError):
    """Un fichier de résultat est illisible ou n'est pas un ``RunResult`` valide."""


def dump_run_result(result: RunResult, path: str | Path) -> None:
    """Écrit le ``RunResult`` en JSON (déterministe)."""
    Path(path).write_text(result.model_dump_json(indent=2), encoding="utf-8")


def load_run_result(path: str | Path) -> RunResult:
    """Charge un ``RunResult`` depuis un fichier JSON."""
    try:
        return RunResult.model_validate_json(
            Path(path).read_text(encoding="utf-8")
        )
    except (OSError, ValidationError) as exc:
        raise RunResultError(f"RunResult illisible : {exc}.") from exc


__all__ = ["RunResultError", "dump_run_result", "load_run_result"]
