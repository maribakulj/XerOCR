"""Métriques de diagnostic texte : cherchabilité, hallucination (couche 3).

Heuristiques **maison** (PLAN_PARITE §5.8b : spécification de départ relue,
valeurs de test dérivées à la main — jamais en exécutant la source).

- ``searchability`` — la question des bibliothèques numériques : quelle part
  des mots de la référence un lecteur retrouve-t-il par recherche plein-texte
  **tolérante** (distance de Levenshtein ≤ 2) dans la transcription ?
  Appariement multi-ensemble : un mot produit ne « retrouve » qu'une seule
  occurrence de référence.
- ``hallucination`` — critique pour les pipelines de post-correction LLM :
  part des trigrammes de caractères de l'hypothèse **absents** de la
  référence (1 − ancrage n-gramme). Un texte fidèle ancre presque tous ses
  trigrammes ; une invention en ancre peu. Plus haut = pire.
"""

from __future__ import annotations

from rapidfuzz.distance import Levenshtein

from xerocr.domain.artifacts import ArtifactType
from xerocr.evaluation.context import DocContext
from xerocr.evaluation.metric import DocumentMetric, Observation, document_metric

#: Distance d'édition tolérée par la recherche plein-texte (mot à mot).
_SEARCH_MAX_DISTANCE = 2
#: Taille des n-grammes d'ancrage de ``hallucination``.
_NGRAM = 3


def _text_pair(ctx: DocContext) -> tuple[str, str]:
    return str(ctx.reference), str(ctx.hypothesis)


@document_metric(
    name="searchability",
    input_types=(ArtifactType.RAW_TEXT, ArtifactType.RAW_TEXT),
    description=(
        "Part des mots de la référence retrouvables dans l'hypothèse à "
        "distance de Levenshtein <= 2 (recherche plein-texte tolérante)."
    ),
    higher_is_better=True,
    tags=frozenset({"text", "diagnostics"}),
)
def searchability(ctx: DocContext) -> Observation | None:
    reference, hypothesis = _text_pair(ctx)
    targets = reference.split()
    if not targets:
        return None
    pool = hypothesis.split()
    used = [False] * len(pool)
    found = 0
    for target in targets:
        for index, word in enumerate(pool):
            if used[index]:
                continue
            if Levenshtein.distance(target, word) <= _SEARCH_MAX_DISTANCE:
                used[index] = True
                found += 1
                break
    return Observation(value=found / len(targets), weight=len(targets))


def _ngrams(text: str) -> list[str]:
    return [text[i : i + _NGRAM] for i in range(len(text) - _NGRAM + 1)]


@document_metric(
    name="hallucination",
    input_types=(ArtifactType.RAW_TEXT, ArtifactType.RAW_TEXT),
    description=(
        "Part des trigrammes de caractères de l'hypothèse absents de la "
        "référence (1 - ancrage) : du texte inventé n'est pas ancré."
    ),
    higher_is_better=False,
    tags=frozenset({"text", "diagnostics"}),
)
def hallucination(ctx: DocContext) -> Observation | None:
    reference, hypothesis = _text_pair(ctx)
    produced = _ngrams(hypothesis)
    if not produced:
        return None  # hypothèse trop courte : rien à ancrer
    anchored = set(_ngrams(reference))
    unanchored = sum(1 for gram in produced if gram not in anchored)
    return Observation(value=unanchored / len(produced), weight=len(produced))


#: Socle diagnostic, collecté explicitement par le registre.
DIAGNOSTIC_METRICS: tuple[DocumentMetric, ...] = (searchability, hallucination)

__all__ = ["DIAGNOSTIC_METRICS", "hallucination", "searchability"]
