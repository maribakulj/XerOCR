"""Cohérence des artefacts de déploiement (Space Docker) — anti-dérive."""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "deploy"


def test_deploy_artifacts_exist() -> None:
    for name in ("Dockerfile", "requirements.txt", "README_SPACE.md"):
        assert (DEPLOY / name).is_file(), f"deploy/{name} manquant"
    assert (DEPLOY / "reports").is_dir()


def test_requirements_cover_core_and_serve() -> None:
    # Le Space n'installe QUE requirements.txt : il doit couvrir le cœur + [serve].
    reqs = (DEPLOY / "requirements.txt").read_text(encoding="utf-8")
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    core = pyproject["project"]["dependencies"]
    serve = pyproject["project"]["optional-dependencies"]["serve"]
    for dep in core + serve:
        name = dep.split(">")[0].split("<")[0].split("=")[0].strip()
        assert name in reqs, f"{name!r} (dépendance requise) absent de requirements.txt"


def test_dockerfile_serves_readonly_vitrine() -> None:
    text = (DEPLOY / "Dockerfile").read_text(encoding="utf-8")
    assert "xerocr" in text and "serve" in text  # lance bien la vitrine
    assert "--port" in text and "7860" in text  # port convention HF Space
    assert "USER xerocr" in text  # non-root


def test_requirements_embark_no_engine() -> None:
    # Vitrine lecture seule : aucun moteur lourd (OCR/LLM) dans l'image servie.
    reqs = (DEPLOY / "requirements.txt").read_text(encoding="utf-8").lower()
    for engine in ("pytesseract", "openai", "torch", "transformers"):
        assert engine not in reqs, f"{engine!r} ne doit pas être dans la vitrine"


def test_space_readme_declares_docker_sdk() -> None:
    header = (DEPLOY / "README_SPACE.md").read_text(encoding="utf-8")
    assert "sdk: docker" in header
    assert "app_port: 7860" in header
