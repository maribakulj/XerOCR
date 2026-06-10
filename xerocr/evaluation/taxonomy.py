"""Taxonomie d'erreurs : classification par règles pures (couche 3).

Transforme « combien d'erreurs » en « quelles erreurs » : chaque mot erroné
est classé par des règles **déterministes et auditables** (aucun ML, aucun
lexique). Heuristique maison (PLAN_PARITE §5.8b : spécification source relue
et **élaguée** — les classes à lexique ``hapax``/``oov_character`` et
l'``abbreviation_error`` à table MUFI ne sont pas portées, cf. D-071).

Classes (ordre de test = priorité) :

- ``segmentation`` — fusion/fragmentation : la concaténation d'un côté égale
  l'autre (« bonjour » ↔ « bon jour ») ;
- ``case`` — casse seule (« Chat » ↔ « chat ») ;
- ``diacritic`` — diacritiques seuls (« été » ↔ « ete ») ;
- ``ligature`` — ligature non résolue (« cœur » ↔ « coeur ») ;
- ``visual`` — confusion morphologique connue (rn↔m, l/1/I, O/0, u↔n, ſ↔s) ;
- ``lacuna`` — mot de la référence absent de l'hypothèse ;
- ``insertion`` — mot de l'hypothèse absent de la référence ;
- ``other`` — substitution résiduelle inclassée.
"""

from __future__ import annotations

import unicodedata
from collections import Counter
from difflib import SequenceMatcher

from xerocr.evaluation.analysis import (
    Analysis,
    PipelineTaxonomy,
    TaxonomyCount,
    TaxonomyPayload,
)

#: Ordre de rendu canonique des classes (déterminisme du payload).
CLASSES: tuple[str, ...] = (
    "segmentation",
    "case",
    "diacritic",
    "ligature",
    "visual",
    "lacuna",
    "insertion",
    "other",
)

#: Ligatures → développement (test dans les deux sens).
_LIGATURES = {
    "œ": "oe", "æ": "ae", "Œ": "OE", "Æ": "AE",
    "ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff",
}

#: Groupes de confusions visuelles → représentant canonique. Appliqué aux
#: **deux** côtés d'une paire déjà fautive (pas de faux positif sur un mot juste).
_VISUAL_CANON = (
    ("rn", "m"),
    ("1", "l"),
    ("I", "l"),
    ("|", "l"),
    ("0", "o"),
    ("O", "o"),
    ("ſ", "s"),
    ("u", "n"),
)


def _strip_diacritics(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if not unicodedata.combining(c)
    )


def _expand_ligatures(text: str) -> str:
    for ligature, expansion in _LIGATURES.items():
        text = text.replace(ligature, expansion)
    return text


def _visual_canonical(text: str) -> str:
    for variant, canon in _VISUAL_CANON:
        text = text.replace(variant, canon)
    return text


def classify_word_pair(reference: str, hypothesis: str) -> str:
    """Classe d'une substitution mot → mot (règles pures, ordre = priorité)."""
    if reference.lower() == hypothesis.lower():
        return "case"
    if _strip_diacritics(reference) == _strip_diacritics(hypothesis):
        return "diacritic"
    if _expand_ligatures(reference) == _expand_ligatures(hypothesis):
        return "ligature"
    if _visual_canonical(reference.lower()) == _visual_canonical(hypothesis.lower()):
        return "visual"
    return "other"


def classify_texts(reference: str, hypothesis: str) -> Counter[str]:
    """Comptage des classes d'erreurs entre deux textes (mots alignés difflib)."""
    counts: Counter[str] = Counter()
    ref_words = reference.split()
    hyp_words = hypothesis.split()
    matcher = SequenceMatcher(a=ref_words, b=hyp_words, autojunk=False)
    for op, a0, a1, b0, b1 in matcher.get_opcodes():
        if op == "equal":
            continue
        ref_seg, hyp_seg = ref_words[a0:a1], hyp_words[b0:b1]
        if op == "delete":
            counts["lacuna"] += len(ref_seg)
            continue
        if op == "insert":
            counts["insertion"] += len(hyp_seg)
            continue
        # replace : fusion/fragmentation d'abord (au niveau du segment).
        if "".join(ref_seg) == "".join(hyp_seg):
            counts["segmentation"] += max(len(ref_seg), len(hyp_seg))
            continue
        for ref_word, hyp_word in zip(ref_seg, hyp_seg, strict=False):
            counts[classify_word_pair(ref_word, hyp_word)] += 1
        # Mots non appariés du segment (longueurs inégales).
        if len(ref_seg) > len(hyp_seg):
            counts["lacuna"] += len(ref_seg) - len(hyp_seg)
        elif len(hyp_seg) > len(ref_seg):
            counts["insertion"] += len(hyp_seg) - len(ref_seg)
    return counts


class TaxonomyCollector:
    """Accumule les classes d'erreurs au fil du scoring d'une vue."""

    def __init__(self) -> None:
        self._counts: dict[str, Counter[str]] = {}

    def observe(self, pipeline: str, reference: str, hypothesis: str) -> None:
        bucket = self._counts.setdefault(pipeline, Counter())
        bucket.update(classify_texts(reference, hypothesis))

    def build(self, view: str) -> Analysis | None:
        rows = tuple(
            PipelineTaxonomy(
                pipeline=pipeline,
                total_errors=sum(bucket.values()),
                counts=tuple(
                    TaxonomyCount(label=label, count=bucket[label])
                    for label in CLASSES
                    if bucket[label] > 0
                ),
            )
            for pipeline, bucket in sorted(self._counts.items())
            if bucket
        )
        if not rows:
            return None
        payload = TaxonomyPayload(classes=CLASSES, pipelines=rows)
        return Analysis(scope="corpus", view=view, payload=payload)


__all__ = ["CLASSES", "TaxonomyCollector", "classify_texts", "classify_word_pair"]
