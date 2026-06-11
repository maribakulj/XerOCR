"""Orchestration vignettes : références → data-URIs (plafonné, pires-d'abord)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from xerocr.app.report_images import build_thumbnails
from xerocr.domain.run import RunManifest
from xerocr.evaluation.result import (
    MetricScore,
    RunDocumentResult,
    RunResult,
)

pytest.importorskip("PIL")
FIXED = datetime(2026, 1, 1, tzinfo=UTC)


def _png(path: Path) -> str:
    from PIL import Image

    Image.new("RGB", (300, 200), (200, 190, 170)).save(path)
    return str(path)


def _doc(doc_id: str, cer: float, image_ref: str | None) -> RunDocumentResult:
    return RunDocumentResult(
        document_id=doc_id, pipeline="tess", view="text", image_ref=image_ref,
        scores=(MetricScore(metric="cer", value=cer, support=1),),
    )


def _result(*documents: RunDocumentResult) -> RunResult:
    manifest = RunManifest(
        run_id="r", corpus_name="demo", n_documents=len(documents),
        code_version="1.0", started_at=FIXED, completed_at=FIXED,
    )
    return RunResult(manifest=manifest, documents=documents)


def test_resolves_references_to_thumbnails(tmp_path: Path) -> None:
    a, b = _png(tmp_path / "a.png"), _png(tmp_path / "b.png")
    thumbs = build_thumbnails(_result(_doc("a", 0.1, a), _doc("b", 0.2, b)))
    assert set(thumbs) == {"a", "b"}
    assert all(v.startswith("data:image/jpeg") for v in thumbs.values())


def test_no_image_ref_returns_empty() -> None:
    assert build_thumbnails(_result(_doc("a", 0.1, None))) == {}


def test_cap_keeps_worst_first(tmp_path: Path) -> None:
    docs = [_doc(f"d{i}", i / 10, _png(tmp_path / f"d{i}.png")) for i in range(4)]
    thumbs = build_thumbnails(_result(*docs), max_docs=2)
    # plafond 2 → garde les pires CER (d3=0.3, d2=0.2)
    assert set(thumbs) == {"d3", "d2"}


def test_missing_file_silently_skipped(tmp_path: Path) -> None:
    ok = _png(tmp_path / "ok.png")
    thumbs = build_thumbnails(
        _result(_doc("ok", 0.1, ok), _doc("gone", 0.2, str(tmp_path / "gone.png")))
    )
    assert set(thumbs) == {"ok"}  # référence morte ignorée (dégradé gracieux)
