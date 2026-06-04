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
#: Libs de moteur autorisées en adapters (ajoutées à la tranche qui les introduit).
#: ``PIL`` : découpage des blocs (``layout/crop``) du pipeline hybride seg→OCR.
#: ``yaml`` : catalogue HTR-United (``htr-united.yml``).
#: ``httpcore`` : moteur de transport de ``httpx`` (toujours co-installé), requis
#: pour l'épinglage d'IP anti-DNS-rebinding (``corpus/_http._PinnedBackend``).
#: ``datasets`` : import de corpus HuggingFace en streaming (extra ``[huggingface]``,
#: import paresseux dans ``corpus/huggingface``).
ADAPTERS_ALLOWED_EXT = ALLOWED_EXT | {
    "pytesseract", "openai", "mistralai", "httpx", "httpcore", "datasets",
    "PIL", "yaml",
}


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
            if mod == "__future__" or top in ADAPTERS_ALLOWED_EXT or top in STDLIB:
                continue
            bad.append(mod)
        if bad:
            offenders[str(path.relative_to(ROOT))] = bad
    assert not offenders, f"imports interdits dans adapters : {offenders}"


#: evaluation parle domain + formats + scipy (Wilcoxon/Friedman) + rapidfuzz
#: (alignement caractère de diacritic_err — c'est la tranche qui l'introduit) ;
#: jiwer/numpy/shapely/PIL s'ajoutent à la tranche qui les introduit.
EVAL_ALLOWED_EXT = ALLOWED_EXT | {"scipy", "rapidfuzz"}


def test_evaluation_imports_are_allowed():
    offenders: dict[str, list[str]] = {}
    for path in (ROOT / "evaluation").rglob("*.py"):
        bad: list[str] = []
        for mod in _imported_modules(path):
            top = mod.split(".")[0]
            if (
                mod == "xerocr"
                or mod.startswith("xerocr.domain")
                or mod.startswith("xerocr.formats")
                or mod.startswith("xerocr.evaluation")
            ):
                continue
            if mod == "__future__" or top in EVAL_ALLOWED_EXT or top in STDLIB:
                continue
            bad.append(mod)
        if bad:
            offenders[str(path.relative_to(ROOT))] = bad
    assert not offenders, f"imports interdits dans evaluation : {offenders}"


#: app câble toutes les couches internes (domain..adapters) ; il orchestre, ne
#: calcule pas. Pas de lib métier directe (métriques/moteurs) — il délègue.
APP_ALLOWED_PKG = (
    "xerocr.domain",
    "xerocr.formats",
    "xerocr.evaluation",
    "xerocr.pipeline",
    "xerocr.adapters",
    "xerocr.app",
)
#: app charge des specs YAML (loader) → ``yaml`` autorisé.
APP_ALLOWED_EXT = ALLOWED_EXT | {"yaml"}


def test_app_imports_are_allowed():
    offenders: dict[str, list[str]] = {}
    for path in (ROOT / "app").rglob("*.py"):
        bad: list[str] = []
        for mod in _imported_modules(path):
            top = mod.split(".")[0]
            if mod == "xerocr" or any(
                mod.startswith(pkg) for pkg in APP_ALLOWED_PKG
            ):
                continue
            if mod == "__future__" or top in APP_ALLOWED_EXT or top in STDLIB:
                continue
            bad.append(mod)
        if bad:
            offenders[str(path.relative_to(ROOT))] = bad
    assert not offenders, f"imports interdits dans app : {offenders}"


def test_reports_imports_are_allowed():
    """reports lit le RunResult : domain + evaluation seulement (jamais app/
    pipeline/adapters). Pas de data-layer, pas de moteur."""
    allowed = ("xerocr.domain", "xerocr.evaluation", "xerocr.reports")
    offenders: dict[str, list[str]] = {}
    for path in (ROOT / "reports").rglob("*.py"):
        bad: list[str] = []
        for mod in _imported_modules(path):
            top = mod.split(".")[0]
            if mod == "xerocr" or any(mod.startswith(pkg) for pkg in allowed):
                continue
            if mod == "__future__" or top in ALLOWED_EXT or top in STDLIB:
                continue
            bad.append(mod)
        if bad:
            offenders[str(path.relative_to(ROOT))] = bad
    assert not offenders, f"imports interdits dans reports : {offenders}"


#: interfaces (couche 8) câble le transport web : FastAPI + son socle ASGI
#: (starlette) + le serveur uvicorn. Ajoutés à la tranche T4 (`serve`).
INTERFACES_ALLOWED_EXT = ALLOWED_EXT | {"fastapi", "starlette", "uvicorn"}


def test_interfaces_imports_are_allowed():
    """interfaces = feuille : peut câbler toutes les couches internes."""
    allowed = (
        "xerocr.domain",
        "xerocr.formats",
        "xerocr.evaluation",
        "xerocr.pipeline",
        "xerocr.adapters",
        "xerocr.app",
        "xerocr.reports",
        "xerocr.interfaces",
    )
    offenders: dict[str, list[str]] = {}
    for path in (ROOT / "interfaces").rglob("*.py"):
        bad: list[str] = []
        for mod in _imported_modules(path):
            top = mod.split(".")[0]
            if mod == "xerocr" or any(mod.startswith(pkg) for pkg in allowed):
                continue
            if mod == "__future__" or top in INTERFACES_ALLOWED_EXT or top in STDLIB:
                continue
            bad.append(mod)
        if bad:
            offenders[str(path.relative_to(ROOT))] = bad
    assert not offenders, f"imports interdits dans interfaces : {offenders}"
