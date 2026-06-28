"""Détection d'hallucinations **par document** (couche 3).

Définition simple et exacte grâce à la **vérité-terrain** : une hallucination =
du texte **inséré** dans la sortie qui n'a **aucune contrepartie dans le GT**. On
l'isole par l'**alignement** des mots (GT ↔ sortie) :

- un mot **mal lu** (coquille, garble) est une **substitution** (« replace ») —
  un mot de la sortie face à un mot du GT → **ce n'est pas une hallucination** ;
- un **passage ajouté** est une **insertion** (« insert ») — des mots de la sortie
  alignés sur un **vide** du GT → **hallucination**.

On ne signale donc que les **runs d'insertion d'au moins ``_MIN_INSERT`` mots**
(un passage, pas un mot parasite isolé). Aucune dépendance, déterministe, lecture
pure. Plafonds de sûreté sur le poids du payload.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from cinoc.evaluation.analysis import (
    Analysis,
    DocumentHallucination,
    DocumentHallucinationPayload,
    HallucinatedBlock,
    PipelineHallucination,
)

#: Longueur minimale d'un passage inséré (mots contigus absents du GT) pour le
#: signaler — au moins une proposition, pas un mot parasite isolé.
_MIN_INSERT = 4
#: Trigrammes pour le score d'ancrage (contexte affiché).
_NGRAM = 3
#: Plafonds de sûreté (poids du payload) : passages par pipeline, longueur de texte.
_MAX_BLOCKS = 20
_MAX_BLOCK_CHARS = 4000


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[^\s]+", text.lower())


def _anchor_score(gt_tokens: list[str], hyp_tokens: list[str]) -> float:
    """Part des trigrammes de la sortie présents dans le GT (contexte, [0,1])."""

    def grams(tokens: list[str]) -> list[tuple[str, ...]]:
        if len(tokens) < _NGRAM:
            return [tuple(tokens)] if tokens else []
        return [tuple(tokens[i : i + _NGRAM]) for i in range(len(tokens) - _NGRAM + 1)]

    hyp_grams = grams(hyp_tokens)
    gt_grams = set(grams(gt_tokens))
    if not hyp_grams:
        return 1.0 if not gt_grams else 0.0
    if not gt_grams:
        return 0.0
    return sum(1 for g in hyp_grams if g in gt_grams) / len(hyp_grams)


def _compute(
    pipeline: str, reference: str, hypothesis: str
) -> PipelineHallucination | None:
    """Analyse d'un (doc, pipeline) ; ``None`` si **aucun** passage inséré.

    Hallucination = run d'``insert`` (mots de la sortie sans contrepartie GT à
    l'alignement) d'au moins ``_MIN_INSERT`` mots. Une substitution (mot mal lu)
    n'est jamais comptée."""
    gt_tokens = _tokenize(reference)
    hyp_tokens = _tokenize(hypothesis)
    matcher = SequenceMatcher(a=gt_tokens, b=hyp_tokens, autojunk=False)
    inserted = 0
    blocks: list[HallucinatedBlock] = []
    for op, _a0, _a1, b0, b1 in matcher.get_opcodes():
        if op != "insert":
            continue  # 'replace' = mot mal lu, 'delete' = omis, 'equal' = correct
        run = b1 - b0
        inserted += run
        if run >= _MIN_INSERT and len(blocks) < _MAX_BLOCKS:
            text = " ".join(hyp_tokens[b0:b1])[:_MAX_BLOCK_CHARS]
            blocks.append(
                HallucinatedBlock(start_token=b0, end_token=b1 - 1, text=text)
            )
    if not blocks:
        return None
    gt_chars = len(reference.strip())
    hyp_chars = len(hypothesis.strip())
    length_ratio = min(hyp_chars / gt_chars, 9.99) if gt_chars else 9.99
    return PipelineHallucination(
        pipeline=pipeline,
        anchor_score=_anchor_score(gt_tokens, hyp_tokens),
        length_ratio=length_ratio,
        net_insertion_rate=inserted / len(hyp_tokens) if hyp_tokens else 0.0,
        gt_words=len(gt_tokens),
        hyp_words=len(hyp_tokens),
        is_hallucinating=True,
        blocks=tuple(blocks),
    )


class DocumentHallucinationCollector:
    """Accumule l'analyse d'hallucination par (document, pipeline) qui en présente."""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, PipelineHallucination]] = {}

    def observe(
        self, pipeline: str, document_id: str, reference: str, hypothesis: str
    ) -> None:
        result = _compute(pipeline, reference, hypothesis)
        if result is not None:
            self._data.setdefault(document_id, {})[pipeline] = result

    def build(self, view: str) -> Analysis | None:
        """Payload des seuls documents où **au moins un** moteur a inséré du texte."""
        if not self._data:
            return None
        documents = tuple(
            DocumentHallucination(
                document_id=doc,
                pipelines=tuple(self._data[doc][p] for p in sorted(self._data[doc])),
            )
            for doc in sorted(self._data)
        )
        return Analysis(
            scope="corpus",
            view=view,
            payload=DocumentHallucinationPayload(documents=documents),
        )


__all__ = ["DocumentHallucinationCollector"]
