"""Aucun héritage Picarones ni symbole supprimé dans le code source."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "xerocr"
FORBIDDEN = [
    "picarones",
    "Picarones",
    "PicaronesError",
    "BaseModule",
    "module_protocol",
    "FactType",
    "DetectorRegistry",
    "LEGACY_VALUE_ALIASES",
    "pipeline_names",
    "BACKLOG_POST_LIVRAISON",
]


def test_no_forbidden_tokens():
    hits: dict[str, list[str]] = {}
    for path in ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        found = [tok for tok in FORBIDDEN if tok in text]
        if found:
            hits[str(path.relative_to(ROOT))] = found
    assert not hits, f"tokens interdits : {hits}"
