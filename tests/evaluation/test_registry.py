"""Registre type-driven : sélection, idempotence, pas d'auto-peuplement."""

from __future__ import annotations

from xerocr.domain.artifacts import ArtifactType
from xerocr.evaluation.registry import MetricRegistry, register_default_metrics


def test_default_metrics_registration_is_idempotent() -> None:
    registry = MetricRegistry()
    register_default_metrics(registry)
    register_default_metrics(registry)
    assert registry.names() == ("cer", "mer", "wer")  # socle texte trié


def test_get_and_select_by_input_types() -> None:
    registry = MetricRegistry()
    register_default_metrics(registry)
    assert registry.document_metric("cer") is not None
    assert registry.document_metric("wer") is not None
    assert registry.document_metric("inconnue") is None
    selected = registry.for_input_types(
        ArtifactType.RAW_TEXT, ArtifactType.RAW_TEXT
    )
    assert {metric.name for metric in selected} == {"cer", "wer", "mer"}
    assert registry.for_input_types(ArtifactType.LAYOUT, ArtifactType.LAYOUT) == ()


def test_fresh_registry_is_empty() -> None:
    assert MetricRegistry().names() == ()


def test_cross_engine_metrics_registered() -> None:
    registry = MetricRegistry()
    register_default_metrics(registry)
    names = {metric.name for metric in registry.cross_engine_metrics()}
    assert "significance_p" in names


def test_fresh_registry_has_no_cross_engine_metrics() -> None:
    assert MetricRegistry().cross_engine_metrics() == ()
