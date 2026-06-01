"""Publication d'un ``RunResult`` vers un dépôt distant (persistance — S3).

Le disque d'un HF Space est **éphémère** : un run calculé est perdu au
redémarrage. Ce module **pousse** le ``RunResult`` JSON vers un dépôt GitHub
(API *contents*) après chaque run réussi, ce qui le rend **durable** et alimente
la vitrine publique (Phase B).

Sécurité & opt-in :

- **Désactivé par défaut.** Sans dépôt **et** jeton (secrets), on renvoie un
  ``NoopPublisher`` : aucune sortie réseau. La vitrine read-only (sans secret)
  reste donc inerte.
- Le **jeton vient d'un secret** (``XEROCR_PUBLISH_TOKEN``) et n'est **jamais
  journalisé** (il ne vit que dans l'en-tête ``Authorization``).
- Aucune dépendance ajoutée : l'appel HTTP réel utilise ``urllib`` (stdlib),
  importé et exécuté seulement à la publication (chemin *live*, hors CI).

La construction de la requête (:func:`build_put_request`) est **pure** et
testée ; seul l'envoi réseau est non couvert.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple, Protocol
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

_API = "https://api.github.com"


class PublishTarget(BaseModel):
    """Cible de publication (dépôt GitHub) — résolue depuis les secrets."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repo: str  # "owner/name"
    token: str
    branch: str = "main"
    subdir: str = "reports"


class PutRequest(NamedTuple):
    """Requête HTTP prête à envoyer (pure, testable sans réseau)."""

    url: str
    headers: dict[str, str]
    body: bytes


class ResultPublisher(Protocol):
    """Publie un ``RunResult`` ; renvoie l'URL distante, ou ``None`` si inactif."""

    def publish(self, name: str, run_result_path: Path) -> str | None: ...


class NoopPublisher:
    """Publisher inactif (aucun secret configuré) : ne fait rien."""

    def publish(self, name: str, run_result_path: Path) -> str | None:
        return None


def build_put_request(target: PublishTarget, name: str, content: bytes) -> PutRequest:
    """Construit la requête *PUT contents* GitHub pour ``<subdir>/<name>.json``."""
    path = quote(f"{target.subdir}/{name}.json", safe="/")
    body = json.dumps(
        {
            "message": f"xerocr: publie le rapport {name}",
            "content": base64.b64encode(content).decode("ascii"),
            "branch": target.branch,
        }
    ).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {target.token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }
    return PutRequest(f"{_API}/repos/{target.repo}/contents/{path}", headers, body)


class GitHubPublisher:
    """Pousse le ``RunResult`` JSON vers un dépôt GitHub (API *contents*)."""

    def __init__(self, target: PublishTarget) -> None:
        self._target = target

    def publish(self, name: str, run_result_path: Path) -> str | None:
        content = run_result_path.read_bytes()
        request = build_put_request(self._target, name, content)
        return self._send(request)

    def _send(self, request: PutRequest) -> str | None:  # pragma: no cover (réseau)
        import urllib.request

        req = urllib.request.Request(
            request.url, data=request.body, headers=request.headers, method="PUT"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        content = payload.get("content") or {}
        return content.get("html_url")


def resolve_publish_target(
    get_env: Callable[[str], str | None] = os.environ.get,
) -> PublishTarget | None:
    """Cible depuis les secrets, ou ``None`` si dépôt **ou** jeton manquant."""
    repo = (get_env("XEROCR_PUBLISH_REPO") or "").strip()
    token = (get_env("XEROCR_PUBLISH_TOKEN") or "").strip()
    if not repo or "/" not in repo or not token:
        return None
    return PublishTarget(
        repo=repo,
        token=token,
        branch=(get_env("XEROCR_PUBLISH_BRANCH") or "main").strip(),
        subdir=(get_env("XEROCR_PUBLISH_DIR") or "reports").strip(),
    )


def resolve_publisher(
    get_env: Callable[[str], str | None] = os.environ.get,
) -> ResultPublisher:
    """``GitHubPublisher`` si configuré (secrets), sinon ``NoopPublisher``."""
    target = resolve_publish_target(get_env)
    return GitHubPublisher(target) if target is not None else NoopPublisher()


__all__ = [
    "GitHubPublisher",
    "NoopPublisher",
    "PublishTarget",
    "PutRequest",
    "ResultPublisher",
    "build_put_request",
    "resolve_publish_target",
    "resolve_publisher",
]
