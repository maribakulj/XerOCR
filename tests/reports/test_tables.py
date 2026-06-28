"""Helpers tabulaires partagés : data-bar, en-tête de métrique (def + tri)."""

from __future__ import annotations

from cinoc.evaluation.result import MetricScore
from cinoc.reports.sections._tables import (
    bar_cell,
    group_header_row,
    metric_th,
    nonempty_metric_indices,
)


def _s(value: float | None, metric: str = "cer") -> MetricScore:
    return MetricScore(metric=metric, value=value, support=1)


def test_group_header_row_merges_consecutive_same_group() -> None:
    # cer, cer_diplo = « caractère » (colspan 2) ; mer = « mot » ; diacritic = « philo »
    row = group_header_row(["cer", "cer_diplo", "mer", "diacritic_err"], "fr", lead=1)
    assert '<th colspan="1"></th>' in row  # cadrage colonne pipeline
    assert 'colspan="2">Erreur · caractère' in row
    assert 'colspan="1">Erreur · mot' in row
    assert "Philologique" in row


def test_group_header_row_unknown_metric_is_blank_cell() -> None:
    row = group_header_row(["mystery"], "fr")
    assert "<th></th>" in row  # métrique hors groupe → cellule vide, pas d'erreur


def test_group_header_row_localized() -> None:
    assert "Character error" in group_header_row(["cer"], "en")


def test_nonempty_metric_indices_hides_all_none_keeps_zero() -> None:
    rows = [(_s(0.0, "cer"), _s(None, "air")), (_s(0.1, "cer"), _s(None, "air"))]
    # cer a des valeurs (dont 0.0 = vraie valeur) → gardé ; air tout None → masqué
    assert nonempty_metric_indices(rows) == [0]


def test_bar_cell_sortable_adds_data_sort() -> None:
    assert 'data-sort="0.250000"' in bar_cell(_s(0.25), 0.5, lang="fr", sortable=True)
    assert "data-sort" not in bar_cell(_s(0.25), 0.5, lang="fr")  # pas de clé de tri
    assert "data-sort" not in bar_cell(
        _s(None), 0.5, lang="fr", sortable=True
    )  # None non triable


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


def test_nonempty_metric_indices_masks_hidden_metrics() -> None:
    # ``mer`` est calculé mais masqué de l'affichage (redondant avec WER) :
    # il ne figure pas dans les indices de colonnes, contrairement à cer/wer.
    from cinoc.evaluation.result import MetricScore
    from cinoc.reports.sections._tables import nonempty_metric_indices

    rows = [
        (
            MetricScore(metric="cer", value=0.1, support=1),
            MetricScore(metric="mer", value=0.2, support=1),
            MetricScore(metric="wer", value=0.3, support=1),
        )
    ]
    keep = nonempty_metric_indices(rows)
    kept_metrics = {rows[0][i].metric for i in keep}
    assert kept_metrics == {"cer", "wer"}  # mer retiré, cer/wer gardés
