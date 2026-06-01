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


def test_flat_dockerfile_has_no_deploy_paths() -> None:
    # Le Dockerfile « racine plate » (dépôt du Space) ne doit copier AUCUN chemin
    # deploy/… : dans le Space, tout est à la racine. (Les commentaires exceptés.)
    text = (DEPLOY / "Dockerfile.space").read_text(encoding="utf-8")
    copy_lines = [
        line for line in text.splitlines() if line.strip().upper().startswith("COPY")
    ]
    assert copy_lines, "Dockerfile.space sans COPY ?"
    assert all("deploy/" not in line for line in copy_lines)


def test_deploy_workflow_uses_secret_not_literal_token() -> None:
    wf = (ROOT / ".github/workflows/deploy-space.yml").read_text(encoding="utf-8")
    assert "secrets.HF_TOKEN" in wf  # le token vient du secret de dépôt
    assert "workflow_dispatch" in wf  # déclenchement manuel disponible
    assert "branches: [main]" in wf  # + auto-sync à chaque push sur main


def test_deploy_smoke_test_has_no_httpx_dependency() -> None:
    # Le smoke-test du déploiement lance le VRAI serveur (uvicorn) + curl :
    # pas de TestClient/httpx (absent de l'image servie). Régression du 1er échec.
    wf = (ROOT / ".github/workflows/deploy-space.yml").read_text(encoding="utf-8")
    assert "uvicorn" in wf and "curl" in wf
    # pas d'IMPORT de TestClient (un commentaire qui le nomme reste autorisé).
    assert "import TestClient" not in wf
    assert "fastapi.testclient" not in wf
