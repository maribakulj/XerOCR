"""Saveur dossier : sidecar (hrefs relatifs) + ``write_report_bundle``.

Le rendu navigateur n'est pas testable en CI : on vérifie la **surface serveur**
(mappings, fichiers écrits) et la **stabilité octet** du HTML à hrefs relatifs.
"""

from __future__ import annotations

import io
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from cinoc.app.report_images import (
    _stem_for,
    build_report_zip,
    build_sidecar_facsimiles,
    build_sidecar_thumbnails,
    write_report_bundle,
)
from cinoc.domain.run import RunManifest
from cinoc.evaluation.result import MetricScore, RunDocumentResult, RunResult
from cinoc.reports import default_report_renderer

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


def _render(result: RunResult, *, title: str, lang: str, images, facsimiles) -> str:
    return default_report_renderer().render(
        result, title=title, lang=lang, images=images, facsimiles=facsimiles
    )


def test_stem_is_deterministic_and_safe() -> None:
    # Slug lisible + empreinte ; même id → même stem ; caractères unsafe nettoyés.
    assert _stem_for("doc1") == _stem_for("doc1")
    stem = _stem_for("path/to/doc 1.png")
    assert "/" not in stem and " " not in stem
    # Deux ids distincts mais slug identique → stems distincts (anti-collision).
    assert _stem_for("a/b") != _stem_for("a-b")
    # Suffixe de variante (fac-similé) distinct de la vignette.
    assert _stem_for("d", suffix="-fac") != _stem_for("d")


def test_sidecar_writes_files_and_returns_relative_hrefs(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    a, b = _png(tmp_path / "a.png"), _png(tmp_path / "b.png")
    assets = tmp_path / "report-assets"
    result = _result(_doc("a", 0.1, a), _doc("b", 0.2, b))
    thumbs = build_sidecar_thumbnails(result, assets)
    assert set(thumbs) == {"a", "b"}
    for doc_id, href in thumbs.items():
        assert href == f"report-assets/{_stem_for(doc_id)}.jpg"
        assert (tmp_path / href).is_file()


def test_sidecar_no_cap_by_default(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    # Caps relâchés (octets sur disque) : 4 documents → 4 fichiers (pas de plafond).
    docs = [_doc(f"d{i}", i / 10, _png(tmp_path / f"d{i}.png")) for i in range(4)]
    thumbs = build_sidecar_thumbnails(_result(*docs), tmp_path / "a")
    assert set(thumbs) == {"d0", "d1", "d2", "d3"}


def test_facsimile_stem_does_not_collide_with_thumbnail(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    img = _png(tmp_path / "x.png")
    assets = tmp_path / "report-assets"
    result = _result(_doc("x", 0.1, img))
    thumb = build_sidecar_thumbnails(result, assets)["x"]
    fac = build_sidecar_facsimiles(result, assets)["x"]
    assert thumb != fac  # vignette et fac-similé du même doc cohabitent
    assert (tmp_path / thumb).is_file() and (tmp_path / fac).is_file()


def test_bundle_writes_html_and_assets_with_relative_hrefs(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    img = _png(tmp_path / "scan.png")
    out = tmp_path / "bundle"
    report = write_report_bundle(_result(_doc("scan", 0.2, img)), out, render=_render)
    assert report == out / "report.html"
    html = report.read_text(encoding="utf-8")
    assert html.startswith("<!DOCTYPE html>")
    href = f"report-assets/{_stem_for('scan')}.jpg"
    assert f'src="{href}"' in html  # référence relative, pas de data-URI
    assert "data:image/jpeg" not in html
    assert (out / href).is_file()


def test_bundle_html_is_byte_stable(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    img = _png(tmp_path / "scan.png")
    result = _result(_doc("scan", 0.2, img))
    first = write_report_bundle(result, tmp_path / "b1", render=_render)
    second = write_report_bundle(result, tmp_path / "b2", render=_render)
    # Hrefs déterministes (dérivés du doc_id) → HTML octet-identique entre dossiers.
    assert first.read_bytes() == second.read_bytes()


def test_bundle_degrades_gracefully_without_images(tmp_path: Path) -> None:
    # Aucune image résoluble (réf morte) → pas d'assets, HTML écrit, pas de crash.
    out = tmp_path / "bundle"
    report = write_report_bundle(
        _result(_doc("d", 0.1, str(tmp_path / "gone.png"))), out, render=_render
    )
    assert report.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")
    assert not (out / "report-assets").exists()  # aucun dérivé écrit


def test_report_zip_packs_html_and_assets(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    img = _png(tmp_path / "scan.png")
    data = build_report_zip(_result(_doc("scan", 0.2, img)), render=_render)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = set(archive.namelist())
        assert "report.html" in names
        href = f"report-assets/{_stem_for('scan')}.jpg"
        assert href in names  # l'image réelle voyage dans le ZIP
        html = archive.read("report.html").decode("utf-8")
        assert html.startswith("<!DOCTYPE html>")
        assert f'src="{href}"' in html  # lien relatif, pas de data-URI
        assert "data:image/jpeg" not in html


def test_report_zip_is_valid_archive_without_images(tmp_path: Path) -> None:
    # Réf morte → ZIP contient au moins report.html, archive valide (pas de crash).
    data = build_report_zip(
        _result(_doc("d", 0.1, str(tmp_path / "gone.png"))), render=_render
    )
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert archive.namelist() == ["report.html"]
