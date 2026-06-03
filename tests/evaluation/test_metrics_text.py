"""CER / WER / MER : valeurs calculées à la main, cas dégénérés, poids, fiches."""

from __future__ import annotations

import pytest

from xerocr.domain.artifacts import ArtifactType
from xerocr.evaluation.context import DocContext
from xerocr.evaluation.errors import EvaluationError
from xerocr.evaluation.metrics.text import (
    cer,
    cer_diplomatic,
    deletion_rate,
    insertion_rate,
    mer,
    wer,
)


def _ctx(reference: object, hypothesis: object) -> DocContext:
    return DocContext(document_id="d", reference=reference, hypothesis=hypothesis)


# ── CER ──────────────────────────────────────────────────────────────────
def test_cer_perfect_match() -> None:
    assert cer.fn(_ctx("abc", "abc")).value == 0.0


def test_cer_one_substitution() -> None:
    assert cer.fn(_ctx("abc", "abx")).value == pytest.approx(1 / 3)


def test_cer_diplomatic_folds_long_s() -> None:
    # « Froiſſart » vs « Froissart » : 2 subs au CER brut, 0 sous repli ſ→s.
    assert cer.fn(_ctx("Froissart", "Froiſſart")).value > 0
    assert cer_diplomatic.fn(_ctx("Froissart", "Froiſſart")).value == 0.0


def test_deletion_rate() -> None:
    # « a b c d » → « a b c » : dernier mot supprimé (1 sur 4 mots de réf).
    obs = deletion_rate.fn(_ctx("a b c d", "a b c"))
    assert obs.value == 0.25 and obs.weight == 4


def test_insertion_rate() -> None:
    # « a b » → « a b c d » : « c » et « d » insérés (2 sur 2 mots de réf).
    obs = insertion_rate.fn(_ctx("a b", "a b c d"))
    assert obs.value == 1.0 and obs.weight == 2


def test_error_profile_bounded_by_wer() -> None:
    # del_rate + ins_rate ≤ wer (le reste = sub_rate = wer − del − ins ≥ 0).
    ctx = _ctx("the quick brown fox", "the fast brown")
    total = deletion_rate.fn(ctx).value + insertion_rate.fn(ctx).value
    assert total <= wer.fn(ctx).value + 1e-9


def test_cer_both_empty() -> None:
    assert cer.fn(_ctx("", "")).value == 0.0


def test_cer_empty_reference_nonempty_hypothesis() -> None:
    assert cer.fn(_ctx("", "x")).value == 1.0


def test_cer_nonempty_reference_empty_hypothesis() -> None:
    assert cer.fn(_ctx("abc", "")).value == 1.0


def test_cer_weight_is_reference_length() -> None:
    # le poids = dénominateur (longueur de réf) : sert au micro-agrégat corpus.
    assert cer.fn(_ctx("abcd", "abxd")).weight == 4
    assert cer.fn(_ctx("", "xyz")).weight == 0  # réf vide → poids nul → exclue du micro


# ── WER ──────────────────────────────────────────────────────────────────
def test_wer_one_substitution() -> None:
    # ["le","chat","noir"] vs ["le","chien","noir"] : 1 sub / 3 mots
    assert wer.fn(_ctx("le chat noir", "le chien noir")).value == pytest.approx(1 / 3)


def test_wer_deletion() -> None:
    assert wer.fn(_ctx("a b c", "a c")).value == pytest.approx(1 / 3)


def test_wer_degenerate() -> None:
    assert wer.fn(_ctx("", "")).value == 0.0
    assert wer.fn(_ctx("", "x")).value == 1.0
    assert wer.fn(_ctx("a b", "")).value == 1.0


def test_wer_weight_is_reference_word_count() -> None:
    assert wer.fn(_ctx("le chat noir", "le chien noir")).weight == 3


# ── MER ──────────────────────────────────────────────────────────────────
def test_mer_substitution() -> None:
    # hits=2 (le, noir), subs=1 (chat/chien) -> 1/3
    assert mer.fn(_ctx("le chat noir", "le chien noir")).value == pytest.approx(1 / 3)


def test_mer_insertion() -> None:
    # hits=2, ins=1 -> 1/3
    assert mer.fn(_ctx("a b", "a b c")).value == pytest.approx(1 / 3)


def test_mer_both_empty() -> None:
    assert mer.fn(_ctx("", "")).value == 0.0


def test_mer_weight_is_hits_plus_edits() -> None:
    # "a b" vs "a b c" : hits=2 + ins=1 -> poids 3 (dénominateur du MER)
    assert mer.fn(_ctx("a b", "a b c")).weight == 3


def test_mer_alignment_is_deterministic_on_ambiguous_input() -> None:
    # "ab" vs "ba" a deux alignements optimaux (2 subs OU 1 ins+1 hit+1 del) :
    # notre back-trace (hit>sub>del>ins) fixe le résultat à 2 subs -> MER 1.0.
    # Comportement VERROUILLÉ ici ; il peut différer de jiwer sur ce type de cas
    # (cf. test_metrics_parity, restreint aux alignements non ambigus).
    assert mer.fn(_ctx("ab", "ba")).value == 1.0


# ── fiches & garde-types ──────────────────────────────────────────────────
def test_fiches() -> None:
    for metric in (cer, wer, mer):
        assert metric.input_types == (ArtifactType.RAW_TEXT, ArtifactType.RAW_TEXT)
        assert metric.spec.higher_is_better is False
    assert {cer.name, wer.name, mer.name} == {"cer", "wer", "mer"}


def test_metrics_reject_non_text() -> None:
    for metric in (cer, wer, mer):
        with pytest.raises(EvaluationError):
            metric.fn(_ctx(123, "x"))
