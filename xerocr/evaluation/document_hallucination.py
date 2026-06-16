"""Détection d'hallucinations **par document** (couche 3).

Pour chaque (document, pipeline), mesure l'**ancrage** (part des trigrammes de la
sortie présents dans le GT), le **ratio de longueur**, le **taux d'insertion
nette** (mots de la sortie
absents du GT), et détecte les **blocs hallucinés** (segments contigus de mots
inventés). Alimente l'analyse d'hallucination du détail document (rapport) — le
graphique le plus parlant pour un moteur qui invente du texte (VLM/LLM, mauvaise
langue). Les seuils sont des **conventions** (pas une autorité externe).
Déterministe, lecture pure.
"""

from __future__ import annotations

import re

from xerocr.evaluation.analysis import (
    Analysis,
    DocumentHallucination,
    DocumentHallucinationPayload,
    HallucinatedBlock,
    PipelineHallucination,
)

#: Trigrammes pour l'ancrage ; seuils de signalement (conventions documentées).
_NGRAM = 3
_ANCHOR_THRESHOLD = 0.5
_LENGTH_RATIO_THRESHOLD = 1.2
#: Bloc halluciné : segment de mots inconnus, tolérance de mots connus, longueur min.
_BLOCK_TOLERANCE = 3
_MIN_BLOCK_LENGTH = 4
#: Plafonds de sûreté (poids du payload) : blocs par pipeline, longueur de texte.
_MAX_BLOCKS = 20
_MAX_BLOCK_CHARS = 4000


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[^\s]+", text.lower())


def _ngrams(tokens: list[str], n: int) -> list[tuple[str, ...]]:
    if len(tokens) < n:
        return [tuple(tokens)] if tokens else []
    return [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def _blocks(
    hyp_tokens: list[str], gt_set: set[str]
) -> list[HallucinatedBlock]:
    """Segments contigus de mots de la sortie absents du GT (tolérance + min)."""
    out: list[HallucinatedBlock] = []
    in_block = False
    start = 0
    known = 0

    def close(end: int) -> None:
        if end - start + 1 >= _MIN_BLOCK_LENGTH and len(out) < _MAX_BLOCKS:
            text = " ".join(hyp_tokens[start : end + 1])[:_MAX_BLOCK_CHARS]
            out.append(
                HallucinatedBlock(start_token=start, end_token=end, text=text)
            )

    for i, tok in enumerate(hyp_tokens):
        if tok not in gt_set:
            if not in_block:
                in_block, start, known = True, i, 0
            else:
                known = 0
        elif in_block:
            known += 1
            if known >= _BLOCK_TOLERANCE:
                close(i - known)
                in_block, known = False, 0
    if in_block:
        close(len(hyp_tokens) - 1)
    return out


def _compute(pipeline: str, reference: str, hypothesis: str) -> PipelineHallucination:
    gt_tokens = _tokenize(reference)
    hyp_tokens = _tokenize(hypothesis)
    gt_set = set(gt_tokens)
    gt_chars = len(reference.strip())
    hyp_chars = len(hypothesis.strip())
    length_ratio = (
        (1.0 if hyp_chars == 0 else 9.99)
        if gt_chars == 0
        else min(hyp_chars / gt_chars, 9.99)
    )
    if not hyp_tokens:
        net_rate = 0.0
    else:
        net_rate = sum(1 for t in hyp_tokens if t not in gt_set) / len(hyp_tokens)
    hyp_ngrams = _ngrams(hyp_tokens, _NGRAM)
    gt_ngrams = set(_ngrams(gt_tokens, _NGRAM))
    if not hyp_ngrams:
        anchor = 1.0 if not gt_ngrams else 0.0
    elif not gt_ngrams:
        anchor = 0.0
    else:
        anchor = sum(1 for ng in hyp_ngrams if ng in gt_ngrams) / len(hyp_ngrams)
    return PipelineHallucination(
        pipeline=pipeline,
        anchor_score=anchor,
        length_ratio=length_ratio,
        net_insertion_rate=net_rate,
        gt_words=len(gt_tokens),
        hyp_words=len(hyp_tokens),
        is_hallucinating=anchor < _ANCHOR_THRESHOLD
        or length_ratio > _LENGTH_RATIO_THRESHOLD,
        blocks=tuple(_blocks(hyp_tokens, gt_set)),
    )


class DocumentHallucinationCollector:
    """Accumule l'analyse d'hallucination par (document, pipeline)."""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, PipelineHallucination]] = {}

    def observe(
        self, pipeline: str, document_id: str, reference: str, hypothesis: str
    ) -> None:
        self._data.setdefault(document_id, {})[pipeline] = _compute(
            pipeline, reference, hypothesis
        )

    def build(self, view: str) -> Analysis | None:
        """Payload par document (ordre déterministe), ``None`` si rien observé."""
        if not self._data:
            return None
        documents = tuple(
            DocumentHallucination(
                document_id=doc,
                pipelines=tuple(
                    self._data[doc][p] for p in sorted(self._data[doc])
                ),
            )
            for doc in sorted(self._data)
        )
        return Analysis(
            scope="corpus",
            view=view,
            payload=DocumentHallucinationPayload(documents=documents),
        )


__all__ = ["DocumentHallucinationCollector"]
