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


def test_requirements_embark_no_heavy_engine() -> None:
    # `requirements.txt` est partagé par la vitrine ET l'image moteur (Étape 1).
    # `pytesseract` (wrapper PUR du binaire, inerte sans lui) y est désormais
    # **attendu** : c'est le socle OCR gratuit du Space. Mais aucun moteur **lourd**
    # (SDK GPU / API cloud à dépendances volumineuses) ne doit y entrer.
    reqs = (DEPLOY / "requirements.txt").read_text(encoding="utf-8").lower()
    assert "pytesseract" in reqs, "pytesseract = socle OCR gratuit (Étape 1)"
    for engine in ("openai", "anthropic", "torch", "transformers", "paddlex"):
        assert engine not in reqs, f"{engine!r} (moteur lourd) hors requirements"


def test_engine_dockerfile_bakes_free_ocr() -> None:
    # Contrat de l'image moteur (Étape 1) : Tesseract + langues baquées, garde
    # anti-deadlock OpenMP, mode public verrouillé, non-root, smoke build fail-fast.
    text = (DEPLOY / "Dockerfile.engine").read_text(encoding="utf-8")
    for token in ("tesseract-ocr-fra", "tesseract-ocr-lat", "tesseract-ocr-eng"):
        assert token in text, f"langue {token} non baquée"
    assert "OMP_THREAD_LIMIT=1" in text  # garde deadlock free-tier (leçon Picarones)
    assert "TESSDATA_PREFIX" in text
    assert "XEROCR_PUBLIC_MODE=true" in text  # fail-closed par défaut sur le Space
    assert "USER xerocr" in text  # non-root
    assert "--list-langs" in text and "grep -qx fra" in text  # smoke fra
    assert "serve" in text and "7860" in text  # lance le serveur


def test_deploy_workflow_builds_engine_and_smoke_ocr() -> None:
    # Le déploiement construit l'image MOTEUR et fait un smoke OCR RÉEL avant push.
    wf = (ROOT / ".github/workflows/deploy-space.yml").read_text(encoding="utf-8")
    assert "Dockerfile.engine" in wf  # le Space déploie le moteur, pas la vitrine
    assert "docker build" in wf and "xerocr-engine" in wf
    assert "tesseract /tmp/hello.png" in wf  # OCR réel d'une image de texte générée


def test_space_readme_declares_docker_sdk() -> None:
    header = (DEPLOY / "README_SPACE.md").read_text(encoding="utf-8")
    assert "sdk: docker" in header
    assert "app_port: 7860" in header


def test_flat_dockerfiles_have_no_deploy_paths() -> None:
    # Les Dockerfiles « racine plate » (dépôt du Space) ne doivent copier AUCUN
    # chemin deploy/… : dans le Space, tout est à la racine. (Commentaires exceptés.)
    # Couvre la vitrine (.space) ET l'image moteur (.engine), tous deux assemblés
    # en racine plate par le workflow de déploiement.
    for name in ("Dockerfile.space", "Dockerfile.engine"):
        text = (DEPLOY / name).read_text(encoding="utf-8")
        copy_lines = [
            line
            for line in text.splitlines()
            if line.strip().upper().startswith("COPY")
        ]
        assert copy_lines, f"{name} sans COPY ?"
        assert all("deploy/" not in line for line in copy_lines), name


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
