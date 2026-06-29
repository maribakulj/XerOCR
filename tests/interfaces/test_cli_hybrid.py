"""Commande CLI ``hybrid`` : transcription de bout en bout (mode précalculé).

Mode ``precomputed`` (déterministe, CI-safe, sans tesseract ni PIL) : le crop est
**désactivé** (``crop=False``), le reconnaisseur lit le texte figé par ``region_id``
sur l'image page entière. Prouve la chaîne CLI → corpus → ``plan_hybrid_run`` →
orchestrateur → ALTO écrits.
"""

from __future__ import annotations

import json
from pathlib import Path

from cinoc.domain.layout import CanonicalLayout, LayoutPage, Region
from cinoc.interfaces.cli import main


def _scene(images: Path, regions: dict[str, str]) -> None:
    images.mkdir()
    (images / "doc1.png").write_bytes(b"\x89PNG stub")
    seg = CanonicalLayout(
        pages=(
            LayoutPage(
                regions=(
                    Region(id="r1", region_type="text"),
                    Region(id="r2", region_type="text"),
                ),
                reading_order=("r1", "r2"),
            ),
        )
    )
    (images / "doc1.layout.json").write_bytes(seg.model_dump_json().encode("utf-8"))
    (images / "doc1.eng.regions.json").write_text(
        json.dumps(regions), encoding="utf-8"
    )


def test_cli_hybrid_precomputed_end_to_end(tmp_path: Path) -> None:
    images = tmp_path / "imgs"
    _scene(images, {"r1": "hello world", "r2": "second block"})
    out = tmp_path / "alto"
    code = main(
        [
            "hybrid",
            str(images),
            "--out",
            str(out),
            "--segmenter",
            "precomputed_layout",
            "--ocr",
            "precomputed_region",
            "--source-label",
            "eng",
        ]
    )
    assert code == 0
    alto = out / "doc1.alto.xml"
    assert alto.is_file()
    # L'ALTO tokenise en mots (un ``<String CONTENT=…>`` par mot) ; le texte
    # reconnu par région survit l'assemblage.
    text = alto.read_text(encoding="utf-8")
    assert all(word in text for word in ("hello", "world", "second", "block"))


def test_cli_hybrid_empty_dir_reports_error(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    # Dossier sans image → TranscriptionError → code 1 (jamais une trace nue).
    assert main(["hybrid", str(empty), "--out", str(tmp_path / "o")]) == 1
