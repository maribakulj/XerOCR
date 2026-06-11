"""Helpers tabulaires partagés : data-bar, en-tête de métrique (def + tri)."""

from __future__ import annotations

from xerocr.evaluation.result import MetricScore
from xerocr.reports.sections._tables import bar_cell, metric_th


def _s(value: float | None) -> MetricScore:
    return MetricScore(metric="cer", value=value, support=1)


def test_bar_cell_sortable_adds_data_sort() -> None:
    assert 'data-sort="0.250000"' in bar_cell(_s(0.25), 0.5, sortable=True)
    assert "data-sort" not in bar_cell(_s(0.25), 0.5)  # défaut : pas de clé de tri
    assert "data-sort" not in bar_cell(_s(None), 0.5, sortable=True)  # None non triable


def test_metric_th_has_definition_and_sort_affordance() -> None:
    th = metric_th("cer", "fr", sortable=True)
    assert 'class="num-cell has-def sortable"' in th
    assert "title=" in th and "CER" in th  # définition au survol (glossaire)
    assert 'aria-sort="none"' in th and 'class="th-sort"' in th  # affordance de tri


def test_metric_th_non_sortable_keeps_definition_only() -> None:
    th = metric_th("cer", "fr")
    assert "has-def" in th and "title=" in th
    assert "sortable" not in th and "aria-sort" not in th


def test_metric_th_unknown_metric_has_no_definition() -> None:
    th = metric_th("unknown_metric", "fr", sortable=True)
    assert "has-def" not in th and "title=" not in th
    assert "sortable" in th  # triable même sans définition


def test_metric_th_localized_definition() -> None:
    assert "word error rate" in metric_th("wer", "en")  # def EN au survol
