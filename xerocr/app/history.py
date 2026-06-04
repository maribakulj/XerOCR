"""Enregistrement d'un run dans l'historique longitudinal (couche 6).

Trait d'union entre le ``RunResult`` (couche 3, agrégats par pipeline/vue) et le
``HistoryStore`` (couche 5, qui ne connaît que des lignes primitives). C'est ici —
et pas dans le store — que vit la connaissance de la forme du ``RunResult`` :
le store reste une persistance pure, réutilisable.
"""

from __future__ import annotations

from xerocr.adapters.storage.history_store import HistoryRecord, HistoryStore
from xerocr.evaluation.result import RunResult


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


__all__ = ["record_run", "records_from_run"]
