"""``FALLBACK_VERSION`` == ``[tool.setuptools_scm] fallback_version``."""

from __future__ import annotations

import tomllib
from pathlib import Path

from xerocr.domain._version_fallback import FALLBACK_VERSION


def test_fallback_matches_pyproject():
    root = Path(__file__).resolve().parents[2]
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["tool"]["setuptools_scm"]["fallback_version"] == FALLBACK_VERSION
