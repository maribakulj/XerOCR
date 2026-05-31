"""Métriques inter-moteurs **statistiques** (scipy). T2 : significativité.

Significativité d'une différence entre pipelines sur une métrique par-document :
**Wilcoxon** apparié (2 moteurs) ou **Friedman** (≥3), sur les **cas complets**
(documents où *tous* les pipelines ont une valeur). ``None`` si support
insuffisant ou aucune différence à tester (pas de variance).
"""

from __future__ import annotations

from scipy import stats  # type: ignore[import-untyped]

from xerocr.evaluation.context import CrossEngineContext
from xerocr.evaluation.metric import CrossEngineMetric, cross_engine_metric

#: En-dessous, pas de test (échantillon apparié trop petit).
_MIN_SUPPORT = 2


@cross_engine_metric(
    name="significance_p",
    description="p-value d'une différence entre pipelines (Wilcoxon/Friedman).",
)
def significance(ctx: CrossEngineContext) -> tuple[float | None, int]:
    pipelines = list(ctx.per_pipeline)
    if len(pipelines) < 2:
        return None, 0
    series = [ctx.per_pipeline[name] for name in pipelines]
    n_documents = len(series[0])
    complete = [
        [column[i] for column in series]
        for i in range(n_documents)
        if all(column[i] is not None for column in series)
    ]
    support = len(complete)
    if support < _MIN_SUPPORT:
        return None, support
    if all(len(set(row)) == 1 for row in complete):
        return None, support  # tous les pipelines égaux : rien à tester
    columns = [list(values) for values in zip(*complete, strict=True)]
    if len(pipelines) == 2:
        result = stats.wilcoxon(columns[0], columns[1])
    else:
        result = stats.friedmanchisquare(*columns)
    return float(result.pvalue), support


#: Socle de métriques inter-moteurs, collecté explicitement par le registre.
CROSS_ENGINE_METRICS: tuple[CrossEngineMetric, ...] = (significance,)

__all__ = ["CROSS_ENGINE_METRICS", "significance"]
