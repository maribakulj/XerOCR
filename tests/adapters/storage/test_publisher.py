"""Publication (S3) : config opt-in depuis secrets + requête PUT pure + Noop."""

from __future__ import annotations

import base64
import json
from collections.abc import Callable
from pathlib import Path

from xerocr.adapters.storage.publisher import (
    GitHubPublisher,
    NoopPublisher,
    PublishTarget,
    build_put_request,
    resolve_publish_target,
    resolve_publisher,
)


def _env(d: dict[str, str]) -> Callable[[str], str | None]:
    return lambda k: d.get(k)


def test_target_none_when_unconfigured() -> None:
    assert resolve_publish_target(_env({})) is None
    # dépôt sans jeton, jeton sans dépôt, dépôt sans « / » → tous None
    assert resolve_publish_target(_env({"XEROCR_PUBLISH_REPO": "o/r"})) is None
    assert resolve_publish_target(_env({"XEROCR_PUBLISH_TOKEN": "t"})) is None
    assert (
        resolve_publish_target(
            _env({"XEROCR_PUBLISH_REPO": "norepo", "XEROCR_PUBLISH_TOKEN": "t"})
        )
        is None
    )


def test_target_populated_with_defaults_and_overrides() -> None:
    t = resolve_publish_target(
        _env({"XEROCR_PUBLISH_REPO": "o/r", "XEROCR_PUBLISH_TOKEN": "tok"})
    )
    assert t is not None
    assert (t.repo, t.token, t.branch, t.subdir) == ("o/r", "tok", "main", "reports")
    t2 = resolve_publish_target(
        _env(
            {
                "XEROCR_PUBLISH_REPO": "o/r",
                "XEROCR_PUBLISH_TOKEN": "tok",
                "XEROCR_PUBLISH_BRANCH": "gh-pages",
                "XEROCR_PUBLISH_DIR": "data",
            }
        )
    )
    assert t2 is not None and (t2.branch, t2.subdir) == ("gh-pages", "data")


def test_resolve_publisher_noop_vs_github() -> None:
    assert isinstance(resolve_publisher(_env({})), NoopPublisher)
    configured = _env({"XEROCR_PUBLISH_REPO": "o/r", "XEROCR_PUBLISH_TOKEN": "t"})
    assert isinstance(resolve_publisher(configured), GitHubPublisher)


def test_build_put_request_shape() -> None:
    target = PublishTarget(repo="o/r", token="sek", branch="main", subdir="reports")
    req = build_put_request(target, "web-abc", b"hello")
    assert req.url == "https://api.github.com/repos/o/r/contents/reports/web-abc.json"
    assert req.headers["Authorization"] == "Bearer sek"
    assert req.headers["Accept"].startswith("application/vnd.github")
    body = json.loads(req.body)
    assert base64.b64decode(body["content"]) == b"hello"
    assert body["branch"] == "main"
    assert "web-abc" in body["message"]


def test_token_only_in_header_not_in_body() -> None:
    req = build_put_request(PublishTarget(repo="o/r", token="SECRET"), "n", b"x")
    assert b"SECRET" not in req.body  # le jeton ne fuit pas dans le corps


def test_noop_publish_returns_none(tmp_path: Path) -> None:
    assert NoopPublisher().publish("x", tmp_path / "x.json") is None
