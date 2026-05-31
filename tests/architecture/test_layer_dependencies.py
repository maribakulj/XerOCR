"""La couche domain n'importe que stdlib + pydantic + pydantic_core."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "xerocr"
DOMAIN = ROOT / "domain"
FORMATS = ROOT / "formats"
ALLOWED_EXT = {"pydantic", "pydantic_core", "typing_extensions", "annotated_types"}
#: La couche formats peut aussi parler XML (lxml) et lire des profils (yaml).
FORMATS_ALLOWED_EXT = ALLOWED_EXT | {"lxml", "yaml"}
STDLIB = set(sys.stdlib_module_names)


def _imported_modules(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                yield "xerocr.domain"
            elif node.module:
                yield node.module


def test_domain_imports_are_pure():
    offenders: dict[str, list[str]] = {}
    for path in DOMAIN.glob("*.py"):
        bad: list[str] = []
        for mod in _imported_modules(path):
            top = mod.split(".")[0]
            if mod == "xerocr" or mod.startswith("xerocr.domain"):
                continue
            if mod == "__future__" or top in ALLOWED_EXT or top in STDLIB:
                continue
            bad.append(mod)
        if bad:
            offenders[path.name] = bad
    assert not offenders, f"imports interdits dans domain : {offenders}"


def test_formats_imports_are_allowed():
    """formats n'importe que stdlib + pydantic + lxml/yaml + domain/formats.
    Jamais une lib de métrique (jiwer/rapidfuzz) ni un moteur OCR."""
    offenders: dict[str, list[str]] = {}
    for path in FORMATS.rglob("*.py"):
        bad: list[str] = []
        for mod in _imported_modules(path):
            top = mod.split(".")[0]
            if (
                mod == "xerocr"
                or mod.startswith("xerocr.domain")
                or mod.startswith("xerocr.formats")
            ):
                continue
            if mod == "__future__" or top in FORMATS_ALLOWED_EXT or top in STDLIB:
                continue
            bad.append(mod)
        if bad:
            offenders[str(path.relative_to(ROOT))] = bad
    assert not offenders, f"imports interdits dans formats : {offenders}"


def test_pipeline_imports_are_allowed():
    """pipeline (couche 4) n'importe que stdlib + pydantic + domain (+ pipeline).
    Aucune lib de moteur ni de métrique : l'exécution est agnostique."""
    offenders: dict[str, list[str]] = {}
    for path in (ROOT / "pipeline").rglob("*.py"):
        bad: list[str] = []
        for mod in _imported_modules(path):
            top = mod.split(".")[0]
            if (
                mod == "xerocr"
                or mod.startswith("xerocr.domain")
                or mod.startswith("xerocr.pipeline")
            ):
                continue
            if mod == "__future__" or top in ALLOWED_EXT or top in STDLIB:
                continue
            bad.append(mod)
        if bad:
            offenders[str(path.relative_to(ROOT))] = bad
    assert not offenders, f"imports interdits dans pipeline : {offenders}"


#: La couche adapters traduit des libs externes (moteurs OCR/LLM) vers le
#: ``Module`` Protocol ; elle peut donc parler domain + pipeline + formats, et
#: ses extras moteur seront ajoutés ici au fil des tranches.
ADAPTERS_ALLOWED_PKG = (
    "xerocr.domain",
    "xerocr.pipeline",
    "xerocr.formats",
    "xerocr.adapters",
)


def test_adapters_imports_are_allowed():
    offenders: dict[str, list[str]] = {}
    for path in (ROOT / "adapters").rglob("*.py"):
        bad: list[str] = []
        for mod in _imported_modules(path):
            top = mod.split(".")[0]
            if mod == "xerocr" or any(
                mod.startswith(pkg) for pkg in ADAPTERS_ALLOWED_PKG
            ):
                continue
            if mod == "__future__" or top in ALLOWED_EXT or top in STDLIB:
                continue
            bad.append(mod)
        if bad:
            offenders[str(path.relative_to(ROOT))] = bad
    assert not offenders, f"imports interdits dans adapters : {offenders}"
