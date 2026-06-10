"""Inférence corrigée : parité Picarones, déterminisme, cas dégénérés."""

from __future__ import annotations

import pytest

from xerocr.evaluation.inference import (
    MIN_SUPPORT,
    bootstrap_ci,
    inference_analysis,
    inference_payload,
    nemenyi_critical_value,
)

#: Jeu apparié 3 pipelines × 8 documents — valeurs de référence calculées avec
#: l'implémentation source (Picarones ``friedman_nemenyi``/``bootstrap``) sur
#: ces données exactes : parité numérique prouvée, pas seulement plausible.
_DATA: dict[str, list[float | None]] = {
    "alpha": [0.10, 0.12, 0.08, 0.11, 0.09, 0.13, 0.10, 0.12],
    "beta": [0.20, 0.22, 0.18, 0.21, 0.19, 0.23, 0.20, 0.22],
    "gamma": [0.15, 0.11, 0.16, 0.12, 0.17, 0.12, 0.15, 0.11],
}


def test_nemenyi_parity_with_source() -> None:
    payload = inference_payload("cer", _DATA)
    assert payload is not None
    assert payload.critical_distance == pytest.approx(1.1715, abs=1e-4)
    assert payload.q_alpha == pytest.approx(2.343, abs=1e-3)
    ranks = {r.pipeline: r.mean_rank for r in payload.mean_ranks}
    assert ranks == pytest.approx({"alpha": 1.375, "gamma": 1.625, "beta": 3.0})
    # Ordre déterministe : tri par (rang, pipeline).
    assert [r.pipeline for r in payload.mean_ranks] == ["alpha", "gamma", "beta"]
    assert payload.tied_groups == (("alpha", "gamma"), ("beta",))
    significant = {
        (pair.a, pair.b): pair.significant for pair in payload.pairwise
    }
    assert significant == {
        ("alpha", "beta"): True,
        ("alpha", "gamma"): False,
        ("beta", "gamma"): True,
    }


def test_bootstrap_parity_and_determinism() -> None:
    values = [v for v in _DATA["alpha"] if v is not None]
    first = bootstrap_ci(values)
    assert first == pytest.approx((0.095, 0.11625))
    assert bootstrap_ci(values) == first  # graine fixe → bit-à-bit
    lower, upper = first
    assert lower <= sum(values) / len(values) <= upper


def test_critical_value_interpolated_between_table_keys() -> None:
    # k=22 ∈ ]20, 25[ → interpolation linéaire (3.544 + 2/5·(3.658−3.544)).
    q, extrapolated = nemenyi_critical_value(22)
    assert q == pytest.approx(3.5896, abs=1e-4)
    assert extrapolated is False


def test_critical_value_extrapolated_beyond_table() -> None:
    q, extrapolated = nemenyi_critical_value(60)
    assert extrapolated is True
    assert q > nemenyi_critical_value(50)[0]  # q croît avec k (conservateur)


def test_below_support_floor_yields_none() -> None:
    short = {name: values[: MIN_SUPPORT - 1] for name, values in _DATA.items()}
    assert inference_payload("cer", short) is None


def test_single_pipeline_yields_none() -> None:
    assert inference_payload("cer", {"alpha": _DATA["alpha"]}) is None


def test_two_pipelines_have_no_posthoc() -> None:
    payload = inference_payload(
        "cer", {"alpha": _DATA["alpha"], "beta": _DATA["beta"]}
    )
    assert payload is not None
    assert payload.critical_distance is None
    assert payload.tied_groups == ()
    assert payload.pairwise == ()
    assert len(payload.mean_ranks) == 2
    assert len(payload.intervals) == 2


def test_none_documents_excluded_from_complete_cases() -> None:
    data = {
        "alpha": [*_DATA["alpha"], None],
        "beta": [*_DATA["beta"], 0.5],
        "gamma": [*_DATA["gamma"], 0.5],
    }
    payload = inference_payload("cer", data)
    assert payload is not None
    assert payload.n_documents == 8  # le 9ᵉ document (None chez alpha) est exclu
    # L'IC marginal de beta utilise, lui, ses 9 valeurs valides.
    intervals = {i.pipeline: i for i in payload.intervals}
    assert intervals["beta"].n_documents == 9
    assert intervals["alpha"].n_documents == 8


def test_payload_serialisation_is_deterministic() -> None:
    analysis = inference_analysis("text", "cer", _DATA)
    assert analysis is not None
    assert analysis.scope == "corpus"
    assert (
        analysis.model_dump_json()
        == inference_analysis("text", "cer", _DATA).model_dump_json()  # type: ignore[union-attr]
    )
