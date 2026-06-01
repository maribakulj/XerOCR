"""CLI ``demo`` : déterminisme (golden octet-stable) + écriture du fichier."""

from __future__ import annotations

from pathlib import Path

from xerocr.interfaces.cli import demo_to_html, main


def test_demo_html_is_deterministic() -> None:
    first = demo_to_html()
    second = demo_to_html()
    assert first == second  # golden octet-stable
    assert first.startswith("<!DOCTYPE html>")
    assert "tesseract" in first
    assert "pero" in first
    assert "démonstration" in first


def test_main_demo_writes_file(tmp_path: Path) -> None:
    output = tmp_path / "rapport.html"
    code = main(["demo", "-o", str(output)])
    assert code == 0
    assert output.is_file()
    assert output.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")
