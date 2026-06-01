"""Métriques de l'axe texte : CER, WER, MER.

Implémentations **déterministes et sans dépendance** (journal D-007) :
- CER = distance d'édition au **caractère** / longueur de référence ;
- WER = distance d'édition au **mot** / nombre de mots de référence ;
- MER (Match Error Rate) = erreurs / (erreurs + correspondances), au mot.

``jiwer`` sert d'**oracle de parité** (tests, dépendance *dev*) — jamais importé
par le code de production. Cas dégénérés (référence vide) explicites.

Coût : le caractère reste en deux lignes (mémoire linéaire) ; seule la matrice
complète de ``_align`` (pour MER) tourne sur des **mots**, peu nombreux.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from xerocr.domain.artifacts import ArtifactType
from xerocr.evaluation.context import DocContext
from xerocr.evaluation.errors import EvaluationError
from xerocr.evaluation.metric import DocumentMetric, Observation, document_metric


def _edit_distance(
    reference: Sequence[object], hypothesis: Sequence[object]
) -> int:
    """Distance de Levenshtein sur deux séquences (deux lignes, O(m) mémoire)."""
    previous = list(range(len(hypothesis) + 1))
    for i, ref_token in enumerate(reference, start=1):
        current = [i]
        for j, hyp_token in enumerate(hypothesis, start=1):
            cost = 0 if ref_token == hyp_token else 1
            current.append(
                min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost)
            )
        previous = current
    return previous[-1]


@dataclass(frozen=True)
class _Alignment:
    """Décompte d'un alignement optimal : correspondances + erreurs typées."""

    hits: int
    substitutions: int
    deletions: int
    insertions: int

    @property
    def edits(self) -> int:
        return self.substitutions + self.deletions + self.insertions


def _align(reference: Sequence[object], hypothesis: Sequence[object]) -> _Alignment:
    """Alignement complet (matrice + backtrace) — pour MER, sur des **mots**."""
    n, m = len(reference), len(hypothesis)
    matrix = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        matrix[i][0] = i
    for j in range(m + 1):
        matrix[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if reference[i - 1] == hypothesis[j - 1] else 1
            matrix[i][j] = min(
                matrix[i - 1][j - 1] + cost,
                matrix[i - 1][j] + 1,
                matrix[i][j - 1] + 1,
            )
    hits = subs = dels = ins = 0
    i, j = n, m
    while i > 0 or j > 0:
        if (
            i > 0
            and j > 0
            and reference[i - 1] == hypothesis[j - 1]
            and matrix[i][j] == matrix[i - 1][j - 1]
        ):
            hits += 1
            i, j = i - 1, j - 1
        elif i > 0 and j > 0 and matrix[i][j] == matrix[i - 1][j - 1] + 1:
            subs += 1
            i, j = i - 1, j - 1
        elif i > 0 and matrix[i][j] == matrix[i - 1][j] + 1:
            dels += 1
            i -= 1
        else:
            ins += 1
            j -= 1
    return _Alignment(hits=hits, substitutions=subs, deletions=dels, insertions=ins)


def _error_rate(edits: int, reference_length: int) -> float:
    """``edits / reference_length`` ; référence vide → 0.0 si exact, sinon 1.0."""
    if reference_length == 0:
        return 0.0 if edits == 0 else 1.0
    return edits / reference_length


def _text_pair(ctx: DocContext) -> tuple[str, str]:
    if not isinstance(ctx.reference, str) or not isinstance(ctx.hypothesis, str):
        raise EvaluationError(
            "métrique texte : reference et hypothesis doivent être du texte."
        )
    return ctx.reference, ctx.hypothesis


@document_metric(
    name="cer",
    input_types=(ArtifactType.RAW_TEXT, ArtifactType.RAW_TEXT),
    description="Character Error Rate : distance d'édition / longueur de référence.",
    higher_is_better=False,
    tags=frozenset({"text", "edit_distance"}),
)
def cer(ctx: DocContext) -> Observation:
    reference, hypothesis = _text_pair(ctx)
    edits = _edit_distance(reference, hypothesis)
    return Observation(
        value=_error_rate(edits, len(reference)), weight=len(reference)
    )


@document_metric(
    name="wer",
    input_types=(ArtifactType.RAW_TEXT, ArtifactType.RAW_TEXT),
    description="Word Error Rate : distance d'édition au mot / nombre de mots de réf.",
    higher_is_better=False,
    tags=frozenset({"text", "edit_distance", "word"}),
)
def wer(ctx: DocContext) -> Observation:
    reference, hypothesis = _text_pair(ctx)
    ref_words, hyp_words = reference.split(), hypothesis.split()
    edits = _edit_distance(ref_words, hyp_words)
    return Observation(
        value=_error_rate(edits, len(ref_words)), weight=len(ref_words)
    )


@document_metric(
    name="mer",
    input_types=(ArtifactType.RAW_TEXT, ArtifactType.RAW_TEXT),
    description="Match Error Rate : erreurs / (erreurs + correspondances), au mot.",
    higher_is_better=False,
    tags=frozenset({"text", "edit_distance", "word"}),
)
def mer(ctx: DocContext) -> Observation:
    reference, hypothesis = _text_pair(ctx)
    alignment = _align(reference.split(), hypothesis.split())
    total = alignment.hits + alignment.edits
    return Observation(
        value=alignment.edits / total if total else 0.0, weight=total
    )


#: Socle de métriques texte, collecté explicitement par le registre.
TEXT_METRICS: tuple[DocumentMetric, ...] = (cer, wer, mer)

__all__ = ["TEXT_METRICS", "cer", "mer", "wer"]
