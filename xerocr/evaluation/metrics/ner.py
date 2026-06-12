"""Scalaire ``ner_f1`` : F1 micro global sur les entités nommées (couche 3).

Jonction ``(ENTITIES, ENTITIES)`` que le registre type-driven accepte sans
modification. Le calcul (appariement IoU + **reprojection R14** des spans
hypothèse en coordonnées GT) vit dans ``evaluation.ner`` ; ici on n'expose que
le F1 global comme ``Observation`` (poids = nombre d'entités GT → micro-agrégat
au niveau corpus). ``None`` si la GT du document ne porte aucune entité (non
applicable — jamais un faux zéro).
"""

from __future__ import annotations

from xerocr.domain.artifacts import ArtifactType
from xerocr.evaluation.context import DocContext
from xerocr.evaluation.errors import EvaluationError
from xerocr.evaluation.metric import DocumentMetric, Observation, document_metric
from xerocr.evaluation.ner import EntitySet, compute_ner, prf


def _entity_pair(ctx: DocContext) -> tuple[EntitySet, EntitySet]:
    if not isinstance(ctx.reference, EntitySet) or not isinstance(
        ctx.hypothesis, EntitySet
    ):
        raise EvaluationError(
            "ner_f1 : reference et hypothesis doivent être des EntitySet."
        )
    return ctx.reference, ctx.hypothesis


@document_metric(
    name="ner_f1",
    input_types=(ArtifactType.ENTITIES, ArtifactType.ENTITIES),
    description=(
        "F1 global sur entités nommées (IoU ≥ 0,5, labels casefold, spans "
        "reprojetés en coordonnées GT). Mesure conjointement OCR + extracteur NER."
    ),
    higher_is_better=True,
    tags=frozenset({"ner", "downstream", "entities"}),
)
def ner_f1(ctx: DocContext) -> Observation | None:
    reference, hypothesis = _entity_pair(ctx)
    if not reference.entities:
        return None  # GT sans entité → non applicable
    counts = compute_ner(reference, hypothesis)
    _precision, _recall, f1 = prf(counts.tp, counts.fp, counts.fn)
    return Observation(value=f1, weight=len(reference.entities))


#: Socle NER, collecté explicitement par le registre.
NER_METRICS: tuple[DocumentMetric, ...] = (ner_f1,)

__all__ = ["NER_METRICS", "ner_f1"]
