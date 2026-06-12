"""Historique longitudinal : enregistrement d'un run + lecture analysée (couche 6).

Trait d'union entre le ``RunResult`` (couche 3, agrégats par pipeline/vue) et le
``HistoryStore`` (couche 5, qui ne connaît que des lignes primitives). C'est ici —
et pas dans le store — que vit la connaissance de la forme du ``RunResult`` :
le store reste une persistance pure, réutilisable.

Dans l'autre sens, ``series_insight`` analyse une série d'enregistrements :
conversion des horodatages ISO (stricte — ligne illisible journalisée puis
écartée, jamais un skip muet) puis tendance OLS + test de rupture de Pettitt
(``evaluation.longitudinal``). Consommé par la page ``/history``.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from xerocr.adapters.storage.history_store import HistoryRecord, HistoryStore
from xerocr.evaluation.longitudinal import (
    PettittResult,
    TrendResult,
    linear_trend,
    pettitt,
)
from xerocr.evaluation.result import RunResult

logger = logging.getLogger(__name__)


def records_from_run(run_result: RunResult) -> tuple[HistoryRecord, ...]:
    """Aplatit un ``RunResult`` en lignes d'historique (métriques applicables)."""
    manifest = run_result.manifest
    completed_at = manifest.completed_at.isoformat()
    records: list[HistoryRecord] = []
    for pipeline in run_result.pipelines:
        for score in pipeline.aggregate:
            if score.value is None:
                continue
            records.append(
                HistoryRecord(
                    run_id=manifest.run_id,
                    completed_at=completed_at,
                    corpus_name=manifest.corpus_name,
                    code_version=manifest.code_version,
                    pipeline=pipeline.pipeline,
                    view=pipeline.view,
                    metric=score.metric,
                    value=score.value,
                )
            )
    return tuple(records)


def record_run(store: HistoryStore, run_result: RunResult) -> int:
    """Persiste les agrégats d'un run dans l'historique ; renvoie le compte."""
    return store.add(records_from_run(run_result))


@dataclass(frozen=True)
class SeriesInsight:
    """Tendance + rupture d'une série (pipeline, vue, métrique) d'historique.

    ``rupture_run_id`` = le **premier run du nouveau régime**, renseigné
    seulement quand la rupture est significative (p ≤ α) — sinon il n'y a
    rien à pointer, quelle que soit l'ampleur du delta.
    """

    trend: TrendResult | None
    rupture: PettittResult | None
    rupture_run_id: str | None


def series_insight(records: Sequence[HistoryRecord]) -> SeriesInsight:
    """Analyse une série d'enregistrements (tendance OLS + rupture Pettitt).

    Les horodatages naïfs sont supposés UTC (le store n'écrit que de
    l'ISO 8601 conscient du fuseau ; la normalisation couvre les données
    importées) ; un horodatage illisible écarte sa ligne **avec warning**.
    """
    rows: list[tuple[datetime, str, float]] = []
    for record in records:
        try:
            stamp = datetime.fromisoformat(record.completed_at)
        except ValueError:
            logger.warning(
                "[history] horodatage illisible ignoré : %r (run %s)",
                record.completed_at,
                record.run_id,
            )
            continue
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=UTC)
        rows.append((stamp, record.run_id, record.value))
    rows.sort(key=lambda row: (row[0], row[1]))
    trend = linear_trend([(stamp, value) for stamp, _, value in rows])
    rupture = pettitt([value for _, _, value in rows])
    rupture_run_id = (
        rows[rupture.boundary][1]
        if rupture is not None and rupture.significant
        else None
    )
    return SeriesInsight(trend=trend, rupture=rupture, rupture_run_id=rupture_run_id)


__all__ = ["SeriesInsight", "record_run", "records_from_run", "series_insight"]
