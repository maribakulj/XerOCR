"""Export CSV d'un ``RunResult`` (couche 7) — lecture pure, zéro recalcul.

Un seul fichier, tableur-compatible : une ligne par score, colonne ``scope``
(``aggregate`` ou ``document``). Ordre = celui du ``RunResult`` (déterministe).
"""

from __future__ import annotations

import csv
import io

from xerocr.evaluation.result import RunResult

_HEADER = ("scope", "view", "pipeline", "document_id", "metric", "value", "support")


def run_result_csv(result: RunResult) -> str:
    """CSV des agrégats puis du détail par-document (UTF-8, séparateur ``,``)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(_HEADER)
    for pipeline in result.pipelines:
        for score in pipeline.aggregate:
            writer.writerow(
                (
                    "aggregate",
                    pipeline.view,
                    pipeline.pipeline,
                    "",
                    score.metric,
                    "" if score.value is None else repr(score.value),
                    "" if score.support is None else score.support,
                )
            )
    for document in result.documents:
        for score in document.scores:
            writer.writerow(
                (
                    "document",
                    document.view,
                    document.pipeline,
                    document.document_id,
                    score.metric,
                    "" if score.value is None else repr(score.value),
                    "" if score.support is None else score.support,
                )
            )
    return buffer.getvalue()


__all__ = ["run_result_csv"]
