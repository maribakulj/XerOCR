"""Socle d'invariance d'échelle : sélection de documents notables + binning."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.result import (
    MetricScore,
    RunDocumentResult,
    RunResult,
)
from xerocr.reports._doc_highlights import (
    HIGHLIGHTS_PER_GROUP,
    DocumentHighlights,
    density_grid,
    histogram,
    notable_documents,
    per_doc_cer_spread,
    per_doc_mean_cer,
)

FIXED = datetime(2026, 1, 1, tzinfo=UTC)


def _doc(doc_id: str, pipeline: str, cer: float | None) -> RunDocumentResult:
    return RunDocumentResult(
        document_id=doc_id, pipeline=pipeline, view="text",
        scores=(MetricScore(metric="cer", value=cer, support=1),),
    )


def _result(*docs: RunDocumentResult) -> RunResult:
    manifest = RunManifest(
        run_id="r", corpus_name="c", n_documents=len(docs), code_version="1.0",
        started_at=FIXED, completed_at=FIXED,
    )
    return RunResult(manifest=manifest, documents=docs)


def test_mean_cer_excludes_none_and_other_metrics() -> None:
    r = _result(_doc("a", "t", 0.2), _doc("a", "p", 0.4), _doc("b", "t", None))
    means = per_doc_mean_cer(r, "text")
    assert means == {"a": 0.30000000000000004}  # moyenne (0.2, 0.4)
    assert "b" not in means  # aucune valeur → exclu (pas de faux zéro)


def test_spread_needs_two_engines() -> None:
    r = _result(_doc("a", "t", 0.2), _doc("a", "p", 0.5), _doc("b", "t", 0.9))
    spread = per_doc_cer_spread(r, "text")
    assert spread == {"a": 0.3}  # 0.5 − 0.2 ; b a un seul moteur


def test_notable_groups_and_dedup_order() -> None:
    r = _result(
        _doc("hard", "t", 0.8), _doc("hard", "p", 0.2),   # mean 0.5, spread 0.6
        _doc("easy", "t", 0.02), _doc("easy", "p", 0.04),  # mean 0.03, spread 0.02
        _doc("mid", "t", 0.3), _doc("mid", "p", 0.3),      # mean 0.3, spread 0.0
    )
    hl = notable_documents(r, "text")
    assert hl.worst[0] == "hard" and hl.best[0] == "easy"
    assert hl.divergent[0] == "hard"  # plus grand écart inter-moteurs
    # union sans doublon, ordre stable : difficiles → discordants → faciles
    assert hl.ordered_ids[0] == "hard"
    assert len(set(hl.ordered_ids)) == len(hl.ordered_ids)
    assert set(hl.ordered_ids) == {"hard", "easy", "mid"}


def test_group_of_primary_category() -> None:
    hl = DocumentHighlights(worst=("a",), best=("a", "b"), divergent=("b",))
    assert hl.group_of("a") == "worst"      # worst l'emporte
    assert hl.group_of("b") == "divergent"  # divergent avant best
    assert hl.group_of("zzz") == ""


def test_notable_empty_without_cer() -> None:
    hl = notable_documents(_result(_doc("a", "t", None)), "text")
    assert hl.ordered_ids == ()


def test_notable_is_bounded_by_per_group() -> None:
    docs = [_doc(f"d{i:03d}", "t", i / 1000.0) for i in range(500)]
    docs += [_doc(f"d{i:03d}", "p", (i + 7) / 1000.0) for i in range(500)]
    hl = notable_documents(_result(*docs), "text")
    assert len(hl.worst) == HIGHLIGHTS_PER_GROUP
    assert len(hl.best) == HIGHLIGHTS_PER_GROUP
    assert len(hl.divergent) == HIGHLIGHTS_PER_GROUP
    assert len(hl.ordered_ids) <= 3 * HIGHLIGHTS_PER_GROUP


def test_histogram_counts_and_edges() -> None:
    assert histogram([], 5) == []
    assert histogram([0.5], 0) == []
    # toutes valeurs égales → tout dans la première classe (pas de div/0)
    assert histogram([0.3, 0.3, 0.3], 4) == [3.0, 0.0, 0.0, 0.0]
    # répartition simple : max tombe dans la dernière classe (borne droite incluse)
    counts = histogram([0.0, 0.0, 1.0], 2)
    assert counts == [2.0, 1.0]
    assert sum(histogram([0.1, 0.4, 0.6, 0.9], 4)) == 4.0  # tous comptés


def test_histogram_shape_invariant_to_count() -> None:
    # même distribution, 10× plus de points → même profil normalisé
    small = histogram([i / 100 for i in range(100)], 10)
    big = histogram([i / 1000 for i in range(1000)], 10)
    assert [round(c / sum(small), 2) for c in small] == [
        round(c / sum(big), 2) for c in big
    ]


def test_density_grid_bins_and_bounds() -> None:
    assert density_grid([], 4, 4) == []
    assert density_grid([(0.1, 0.1)], 0, 4) == []
    # deux points dans la même cellule → une sortie, compte 2
    cells = density_grid([(0.1, 0.1), (0.12, 0.08)], 4, 4)
    assert len(cells) == 1 and cells[0][2] == 2.0
    # borne supérieure : jamais plus de nx*ny cellules quel que soit le nombre
    many = density_grid([(i / 1000, (i * 7 % 1000) / 1000) for i in range(1000)], 8, 8)
    assert len(many) <= 8 * 8


def test_density_grid_is_deterministic() -> None:
    pts = [(0.2, 0.8), (0.9, 0.1), (0.2, 0.81)]
    assert density_grid(pts, 5, 5) == density_grid(pts, 5, 5)
