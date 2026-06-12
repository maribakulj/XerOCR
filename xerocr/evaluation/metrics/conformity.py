"""Métrique de conformité HIPE : ``cmer`` — MER au **caractère** (couche 3).

Le scorer HIPE-OCRepair classe sur le Match Error Rate caractère
``(S+D+I)/(H+S+D+I)`` — **borné [0, 1]**, contrairement au CER classique qu'un
modèle génératif fait dépasser 100 % (SPEC_HIPE §1.1). ``mer`` (mot) existe déjà
au socle ; ``cmer`` est son pendant caractère. Comptes H/S/D/I via
``rapidfuzz.editops`` (la plein-matrice maison de ``text._align`` serait trop
coûteuse sur des documents entiers — même arbitrage que ``diacritic_err``).

Conformité prouvée par parité ``jiwer.process_characters`` (oracle de test,
même formule que le scorer) + golden vs scorer épinglé (job CI 3.12).
"""

from __future__ import annotations

from rapidfuzz.distance import Levenshtein

from xerocr.domain.artifacts import ArtifactType
from xerocr.evaluation.context import DocContext
from xerocr.evaluation.errors import EvaluationError
from xerocr.evaluation.metric import DocumentMetric, Observation, document_metric


@document_metric(
    name="cmer",
    input_types=(ArtifactType.RAW_TEXT, ArtifactType.RAW_TEXT),
    description=(
        "Match Error Rate caractère : (S+D+I)/(H+S+D+I), borné [0,1] — "
        "la métrique de classement du scorer HIPE-OCRepair."
    ),
    higher_is_better=False,
    tags=frozenset({"text", "conformity"}),
)
def cmer(ctx: DocContext) -> Observation:
    """``edits / (longueur_référence + insertions)`` ; deux textes vides → 0.0.

    ``weight`` = le dénominateur ``H+S+D+I`` : le micro-agrégat du runner
    (Σ erreurs / Σ dénominateurs) reproduit exactement le ``cmer_micro`` du
    scorer (somme des comptes puis ratio, SPEC_HIPE §4.1).
    """
    if not isinstance(ctx.reference, str) or not isinstance(ctx.hypothesis, str):
        raise EvaluationError("cmer : reference et hypothesis doivent être du texte.")
    substitutions = deletions = insertions = 0
    for op in Levenshtein.editops(ctx.reference, ctx.hypothesis):
        if op.tag == "replace":
            substitutions += 1
        elif op.tag == "delete":
            deletions += 1
        else:
            insertions += 1
    # H + S + D = longueur de la référence (alignement complet de la référence).
    total = len(ctx.reference) + insertions
    edits = substitutions + deletions + insertions
    return Observation(value=edits / total if total else 0.0, weight=total)


#: Métriques de conformité, collectées explicitement par le registre.
CONFORMITY_METRICS: tuple[DocumentMetric, ...] = (cmer,)

__all__ = ["CONFORMITY_METRICS", "cmer"]
