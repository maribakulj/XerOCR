"""Fidélité textuelle : tokens rares (multiset) + modernisation lexicale.

Valeurs **dérivées à la main** sur un corpus de 3 documents court (fréquences
calculées à la main : `le`=2, `roi`=3, `charles`=2, `louis`=1, `est`=1 →
rares ≤ 2 = {charles, est, le, louis}, `roi` exclu).
"""

from __future__ import annotations

from xerocr.evaluation.analysis import TextualFidelityPayload
from xerocr.evaluation.textual_fidelity import (
    TextualFidelityCollector,
    corpus_frequencies,
    modernization_counts,
    rare_recall_counts,
    rare_tokens,
    tokenize,
)

_REFS = ["le roi Charles", "le roi Louis", "Charles est roi"]


def test_tokenize_lowercases_and_keeps_contractions() -> None:
    assert tokenize("L'an Peut-être, Roi.") == ["l'an", "peut-être", "roi"]


def test_rare_set_excludes_frequent_tokens() -> None:
    freq = corpus_frequencies(_REFS)
    assert freq["roi"] == 3 and freq["louis"] == 1
    assert rare_tokens(freq, 2) == frozenset({"charles", "est", "le", "louis"})


def test_rare_recall_multiset_missed() -> None:
    rare = rare_tokens(corpus_frequencies(_REFS), 2)
    # GT « le roi Louis » : rares = le, louis ; hyp perd louis (→ loys, hors rares).
    assert rare_recall_counts("le roi Louis", "le roi Loys", rare) == (2, 1, ["louis"])


def test_rare_recall_perfect_and_absent() -> None:
    rare = rare_tokens(corpus_frequencies(_REFS), 2)
    assert rare_recall_counts("Charles est roi", "Charles est roi", rare) == (2, 2, [])
    # GT sans token rare → non applicable (0, 0, []).
    assert rare_recall_counts("roi roi", "roi", rare) == (0, 0, [])


def test_rare_recall_repeated_token_multiplicity() -> None:
    rare = frozenset({"dupont"})
    # « Dupont » 2× en GT, 1× en hyp → 1 rappelé, 1 manqué.
    assert rare_recall_counts("Dupont et Dupont", "Dupont et Martin", rare) == (
        2,
        1,
        ["dupont"],
    )


def test_modernization_replace_and_delete() -> None:
    slots = modernization_counts("maistre nostre sage", "maitre nostre")
    # maistre → maitre (modernisé) ; nostre conservé ; sage supprimé (∅).
    assert slots["maistre"].n_modernized == 1
    assert dict(slots["maistre"].variants) == {"maitre": 1}
    assert slots["nostre"].n_modernized == 0
    assert dict(slots["sage"].variants) == {"∅": 1}


def _payload(collector: TextualFidelityCollector) -> TextualFidelityPayload:
    analysis = collector.build("text")
    assert analysis is not None
    payload = analysis.payload
    assert isinstance(payload, TextualFidelityPayload)
    return payload


def test_collector_aggregates_recall_and_modernization() -> None:
    collector = TextualFidelityCollector()
    collector.observe("p", "d1", "le roi Charles", "le roi Charles")
    collector.observe("p", "d2", "le roi Louis", "le roi Loys")
    collector.observe("p", "d3", "Charles est roi", "charles est roi")
    payload = _payload(collector)
    assert payload.max_freq == 2
    (row,) = payload.pipelines
    # recall : d1=2/2 · d2=1/2 (louis manqué) · d3=2/2 → 5/6.
    assert row.n_rare_reference == 6 and row.n_rare_recalled == 5
    assert row.rare_recall == 5 / 6
    assert row.missed == ("louis",)
    # seule modernisation : louis → loys (rate 1.0).
    (token,) = row.modernization
    assert token.token == "louis" and token.rate == 1.0
    assert token.variants[0].form == "loys" and token.variants[0].count == 1


def test_collector_recall_none_without_rare_tokens() -> None:
    # Corpus où tout token est fréquent (roi ×6) → aucun rare → recall None.
    collector = TextualFidelityCollector()
    collector.observe("p", "d1", "roi roi roi", "roi roi roi")
    collector.observe("p", "d2", "roi roi roi", "roi roi")
    payload = _payload(collector)
    (row,) = payload.pipelines
    assert row.n_rare_reference == 0 and row.rare_recall is None


def test_collector_empty_build_is_none() -> None:
    assert TextualFidelityCollector().build("text") is None
