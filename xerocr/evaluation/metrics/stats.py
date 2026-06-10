"""Métriques inter-moteurs **statistiques** (scipy) : significativité.

Significativité d'une différence entre pipelines sur une métrique par-document :
**Wilcoxon** apparié (2 moteurs) ou **Friedman** (≥3), sur les **cas complets**
(documents où *tous* les pipelines ont une valeur). ``None`` si support
insuffisant ou aucune différence à tester (pas de variance).
"""

from __future__ import annotations

from scipy import stats  # type: ignore[import-untyped]

from xerocr.evaluation.context import CrossEngineContext
from xerocr.evaluation.inference import MIN_SUPPORT
from xerocr.evaluation.metric import CrossEngineMetric, cross_engine_metric

#: Plancher de **puissance** (pas seulement de calcul) : sous ~6 paires, un
#: Wilcoxon bilatéral ne peut **pas** atteindre p < 0,05 (n=6 → p_min exact ≈
#: 0,031), et un Friedman à 2-3 blocs est dégénéré. Renvoyer une p-value sous ce
#: seuil serait un artefact de petit n présenté comme un verdict → on rend ``None``.
#: Source unique partagée avec l'inférentiel corrigé (``evaluation.inference``).
_MIN_SUPPORT = MIN_SUPPORT


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
    try:
        if len(pipelines) == 2:
            result = stats.wilcoxon(columns[0], columns[1])
        else:
            result = stats.friedmanchisquare(*columns)
    except ValueError:  # pragma: no cover -- filet : entrée dégénérée résiduelle
        # scipy refuse un échantillon que nos gardes n'ont pas écarté
        # (ex. différences toutes nulles après abandon des ex æquo) → non testable.
        return None, support
    return float(result.pvalue), support


#: Socle de métriques inter-moteurs, collecté explicitement par le registre.
CROSS_ENGINE_METRICS: tuple[CrossEngineMetric, ...] = (significance,)

__all__ = ["CROSS_ENGINE_METRICS", "significance"]
