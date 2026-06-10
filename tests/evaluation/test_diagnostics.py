"""Diagnostic : métriques + assemblage — valeurs dérivées **à la main**.

Règle d'ancrage (PLAN_PARITE §5.8b) : heuristiques maison — chaque valeur
attendue est calculée sur papier, jamais générée en exécutant la source.
"""

from __future__ import annotations

import pytest

from xerocr.evaluation.context import DocContext
from xerocr.evaluation.diagnostics import (
    DiagnosticsCollector,
    char_confusions,
    line_cers,
)
from xerocr.evaluation.metrics.diagnostics import hallucination, searchability
from xerocr.evaluation.result import MetricScore


def _ctx(reference: str, hypothesis: str) -> DocContext:
    return DocContext(document_id="d1", reference=reference, hypothesis=hypothesis)


# --- searchability : recall de mots à distance <= 2 ------------------------


def test_searchability_tolerates_two_edits() -> None:
    # « chat » vs « chot » : distance 1 → retrouvé ; « noir » vs « noir » : 0.
    obs = searchability.fn(_ctx("le chat noir", "le chot noir"))
    assert obs is not None
    assert obs.value == pytest.approx(1.0)
    assert obs.weight == 3


def test_searchability_counts_missing_words() -> None:
    # « xxxxxxx » est à distance > 2 de tous les mots produits → 2/3 retrouvés.
    obs = searchability.fn(_ctx("le chat noir", "le xxxxxxx noir"))
    assert obs is not None
    assert obs.value == pytest.approx(2 / 3)


def test_searchability_multiset_one_match_per_occurrence() -> None:
    # Réf : « aa aa » (2 occurrences) ; hyp : « aa » (1 seule) → recall 1/2.
    obs = searchability.fn(_ctx("aa aa", "aa"))
    assert obs is not None
    assert obs.value == pytest.approx(0.5)


def test_searchability_empty_reference_is_not_applicable() -> None:
    assert searchability.fn(_ctx("", "texte")) is None


# --- hallucination : trigrammes non ancrés ----------------------------------


def test_hallucination_zero_when_verbatim() -> None:
    obs = hallucination.fn(_ctx("bonjour", "bonjour"))
    assert obs is not None
    assert obs.value == 0.0
    assert obs.weight == 5  # « bonjour » : 7 chars → 5 trigrammes


def test_hallucination_hand_computed_on_invented_suffix() -> None:
    # Réf « abcdef » ancre {abc,bcd,cde,def}. Hyp « abcxyz » produit
    # {abc,bcx,cxy,xyz} → 3 non ancrés sur 4 = 0.75.
    obs = hallucination.fn(_ctx("abcdef", "abcxyz"))
    assert obs is not None
    assert obs.value == pytest.approx(0.75)
    assert obs.weight == 4


def test_hallucination_short_hypothesis_not_applicable() -> None:
    assert hallucination.fn(_ctx("abcdef", "ab")) is None


# --- confusions de caractères ------------------------------------------------


def test_char_confusions_pairs_replaced_segment_positionally() -> None:
    # « rn » lu « m » n'est pas positionnel ; ici cas simple : e→o deux fois.
    pairs = char_confusions("le chevre", "lo chovre")
    assert pairs[("e", "o")] == 2


def test_line_cers_hand_computed() -> None:
    lines = line_cers("abcd\nefgh", "abxd\nefgh")
    # Ligne 0 : 1 édition / 4 chars = 0.25 ; ligne 1 : 0.
    assert lines == [(0, 0.25, "abcd", "abxd"), (1, 0.0, "efgh", "efgh")]


def test_line_cers_missing_hypothesis_line_is_full_error() -> None:
    lines = line_cers("abcd\nefgh", "abcd")
    assert lines[1] == (1, 1.0, "efgh", "")


# --- assemblage --------------------------------------------------------------


def test_collector_builds_sorted_payload() -> None:
    collector = DiagnosticsCollector()
    collector.observe("alpha", "d1", "abcd\nefgh", "abxd\nefgh")
    collector.observe("beta", "d1", "abcd\nefgh", "xxxx\nefgh")
    analysis = collector.build(
        "text",
        "cer",
        ["d1"],
        {
            "alpha": [MetricScore(metric="cer", value=0.125, support=8)],
            "beta": [MetricScore(metric="cer", value=0.5, support=8)],
        },
    )
    assert analysis is not None
    payload = analysis.payload
    assert payload.kind == "diagnostics"
    # Pire ligne d'abord : beta ligne 0 (CER 1.0) avant alpha ligne 0 (0.25).
    assert payload.worst_lines[0].pipeline == "beta"
    assert payload.worst_lines[0].cer == pytest.approx(1.0)
    assert payload.worst_lines[1].pipeline == "alpha"
    # Confusions triées par pipeline ; alpha : c→x une fois.
    assert payload.confusions[0].pipeline == "alpha"
    assert payload.confusions[0].pairs[0].count == 1
    # Difficulté : moyenne des CER des pipelines scorés.
    assert payload.hardest_documents[0].mean_cer == pytest.approx(0.3125)
    assert payload.hardest_documents[0].n_pipelines == 2


def test_collector_without_observation_yields_none() -> None:
    assert DiagnosticsCollector().build("text", "cer", [], {}) is None


def test_payload_is_deterministic() -> None:
    def build() -> str:
        collector = DiagnosticsCollector()
        collector.observe("alpha", "d1", "abcd", "abxd")
        analysis = collector.build(
            "text", "cer", ["d1"],
            {"alpha": [MetricScore(metric="cer", value=0.25, support=4)]},
        )
        assert analysis is not None
        return analysis.model_dump_json()

    assert build() == build()
