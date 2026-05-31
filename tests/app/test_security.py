"""``validated_path`` : confine sous base ; rejette traversal / absolu / nul."""

from __future__ import annotations

from pathlib import Path

import pytest

from xerocr.app.security import PathSecurityError, validated_path


def test_relative_resolves_under_base(tmp_path: Path) -> None:
    assert validated_path("images/doc1.png", tmp_path) == (
        tmp_path / "images/doc1.png"
    ).resolve()


def test_traversal_rejected(tmp_path: Path) -> None:
    with pytest.raises(PathSecurityError):
        validated_path("../../etc/passwd", tmp_path)


def test_absolute_outside_base_rejected(tmp_path: Path) -> None:
    with pytest.raises(PathSecurityError):
        validated_path("/etc/passwd", tmp_path)


def test_absolute_inside_base_accepted(tmp_path: Path) -> None:
    inside = tmp_path / "a" / "b.txt"
    assert validated_path(str(inside), tmp_path) == inside.resolve()


@pytest.mark.parametrize("bad", ["", "   ", "a\x00b"])
def test_empty_or_null_rejected(bad: str, tmp_path: Path) -> None:
    with pytest.raises(PathSecurityError):
        validated_path(bad, tmp_path)


def test_must_exist(tmp_path: Path) -> None:
    with pytest.raises(PathSecurityError):
        validated_path("absent.txt", tmp_path, must_exist=True)
    (tmp_path / "here.txt").write_text("x", encoding="utf-8")
    assert validated_path("here.txt", tmp_path, must_exist=True) == (
        tmp_path / "here.txt"
    ).resolve()
