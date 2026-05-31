"""Métriques de l'axe texte. T1 : CER (Character Error Rate).

CER = distance d'édition (Levenshtein) au caractère / longueur de la référence.
Implémentation **déterministe et sans dépendance** (journal D-007) ; ``jiwer``
servira d'**oracle de parité** à la tranche T2. Cas dégénérés explicites.
"""

from __future__ import annotations

from xerocr.domain.artifacts import ArtifactType
from xerocr.evaluation.context import DocContext
from xerocr.evaluation.errors import EvaluationError
from xerocr.evaluation.metric import DocumentMetric, document_metric


def _levenshtein(reference: str, hypothesis: str) -> int:
    """Distance d'édition au caractère (DP en O(n·m), déterministe)."""
    previous = list(range(len(hypothesis) + 1))
    for i, ref_char in enumerate(reference, start=1):
        current = [i]
        for j, hyp_char in enumerate(hypothesis, start=1):
            cost = 0 if ref_char == hyp_char else 1
            current.append(
                min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost)
            )
        previous = current
    return previous[-1]


def _cer_value(reference: str, hypothesis: str) -> float:
    if not reference:
        return 0.0 if not hypothesis else 1.0
    if not hypothesis:
        return 1.0
    return _levenshtein(reference, hypothesis) / len(reference)


@document_metric(
    name="cer",
    input_types=(ArtifactType.RAW_TEXT, ArtifactType.RAW_TEXT),
    description="Character Error Rate : distance d'édition / longueur de référence.",
    higher_is_better=False,
    tags=frozenset({"text", "edit_distance"}),
)
def cer(ctx: DocContext) -> float:
    if not isinstance(ctx.reference, str) or not isinstance(ctx.hypothesis, str):
        raise EvaluationError("cer : reference et hypothesis doivent être du texte.")
    return _cer_value(ctx.reference, ctx.hypothesis)


#: Socle de métriques texte, collecté explicitement par le registre.
TEXT_METRICS: tuple[DocumentMetric, ...] = (cer,)

__all__ = ["TEXT_METRICS", "cer"]
