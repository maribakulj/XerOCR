"""Preuve réelle « brancher sans forker » : un paquet **pip-installé** dont
l'entry-point ``xerocr.modules`` est **auto-découvert** par le vrai chemin
``importlib.metadata`` (pas un loader injecté).

Isolé : installation dans un ``--target`` temporaire + découverte exécutée dans
un **process enfant** (l'env de la session n'est pas pollué → les autres tests,
dont ``test_default_loader_runs_clean``, restent valides). Skippe proprement si
``pip``/build indisponible (offline CI) — ne casse jamais la CI.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

_PKG_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "sample_plugin_pkg"


@pytest.mark.slow
def test_pip_installed_plugin_is_auto_discovered(tmp_path: Path) -> None:
    target = tmp_path / "site"
    install = subprocess.run(
        [
            sys.executable, "-m", "pip", "install", "--no-deps",
            "--target", str(target), str(_PKG_DIR),
        ],
        capture_output=True,
        text=True,
    )
    if install.returncode != 0:
        pytest.skip(f"pip install indisponible : {install.stderr[-200:]}")

    # Process enfant : --target sur sys.path → vraie découverte du dist installé.
    script = textwrap.dedent(
        f"""
        import sys
        sys.path.insert(0, {str(target)!r})
        from xerocr.app.modules import ModuleRegistry, discover_plugins
        registry = ModuleRegistry()
        print(",".join(discover_plugins(registry, enabled=True)))
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )
    # Le paquet tiers réellement installé est découvert via importlib.metadata.
    assert "sample_pkg_seg" in result.stdout
