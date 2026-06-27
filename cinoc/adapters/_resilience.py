"""Résilience des appels réseau (couche 5, adapters) : cap de concurrence + retry.

Deux mécanismes, **par défaut, sans configuration**, pour qu'un run depuis l'UI
web (n'importe qui) ne sature pas une API instable :

- **Cap de concurrence par fournisseur** (``network_slot``) : un sémaphore borné
  *par fournisseur* (Mistral, OpenAI… chacun le sien) → au plus N appels réseau
  simultanés, quel que soit le nombre de threads du runner. C'est le fix
  structurel du pool global partagé (Pero local + LLM réseau dans un même run).
- **Retry borné** (``call_resilient``) : sur 429/5xx, attend ``Retry-After`` si le
  serveur l'indique, sinon un backoff exponentiel borné + gigue, puis recommence.

Stdlib pure (aucune dépendance). **Déterminisme (invariant §12)** : ces mécanismes
ne changent que le *timing*, jamais la valeur renvoyée → le ``RunResult`` reste
byte-identique. ``N`` = ``CINOC_NETWORK_CONCURRENCY`` (défaut 3, plancher 1).
"""

from __future__ import annotations

import logging
import os
import random
import threading
import time
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

#: Plafond par défaut d'appels réseau concurrents **par fournisseur** (anti-429).
_DEFAULT_LIMIT = 3
_LIMIT_ENV = "CINOC_NETWORK_CONCURRENCY"
#: Politique de retry : tentatives + backoff exponentiel borné (secondes).
_DEFAULT_ATTEMPTS = 5
_BASE_BACKOFF = 1.0
_MAX_BACKOFF = 30.0
#: Statuts HTTP retentés : 429 (rate limit) + 5xx transitoires (instabilité).
_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})

#: Registre process-global des sémaphores, créés paresseusement (aucun effet de
#: bord à l'import). Protégé par un verrou : ``network_slot`` est thread-safe.
_SEMAPHORES: dict[str, threading.BoundedSemaphore] = {}
_REGISTRY_LOCK = threading.Lock()


def _network_limit() -> int:
    """Plafond effectif depuis l'environnement (défaut ``_DEFAULT_LIMIT``)."""
    raw = os.environ.get(_LIMIT_ENV)
    if raw is None:
        return _DEFAULT_LIMIT
    try:
        value = int(raw)
    except ValueError:
        logger.warning(
            "[resilience] %s=%r invalide (entier attendu) — défaut %d.",
            _LIMIT_ENV,
            raw,
            _DEFAULT_LIMIT,
        )
        return _DEFAULT_LIMIT
    return max(1, value)


def network_slot(provider: str) -> AbstractContextManager[bool]:
    """Sémaphore borné **du fournisseur** : ``with network_slot("mistral"): …``.

    Au plus ``_network_limit()`` détenteurs simultanés par fournisseur. Chaque
    fournisseur a son quota propre (un run OpenAI + Mistral ne les fait pas se
    partager le budget). Le plafond est figé à la première création du fournisseur
    (lecture d'environnement unique, déterministe pour la durée du process)."""
    with _REGISTRY_LOCK:
        sem = _SEMAPHORES.get(provider)
        if sem is None:
            sem = threading.BoundedSemaphore(_network_limit())
            _SEMAPHORES[provider] = sem
    return sem


def _default_jitter() -> float:
    return random.uniform(0.0, 1.0)


def _backoff(attempt: int, jitter: Callable[[], float]) -> float:
    """Backoff exponentiel borné + gigue (désynchronise les threads concurrents)."""
    return min(_MAX_BACKOFF, _BASE_BACKOFF * (2.0**attempt)) + jitter()


def http_is_retryable(exc: BaseException) -> bool:
    """Vrai si l'exception SDK porte un statut HTTP transitoire (429/5xx).

    Duck-typing assumé : les SDK httpx (mistralai/openai/anthropic) exposent
    ``status_code``. Une erreur sans statut (réseau coupé, bug local) n'est **pas**
    retentée — on ne masque pas un vrai défaut."""
    return getattr(exc, "status_code", None) in _RETRYABLE_STATUS


def http_retry_after(exc: BaseException) -> float | None:
    """Délai ``Retry-After`` (secondes, borné) si le serveur l'indique, sinon ``None``.

    Sonde l'en-tête sur ``exc.response.headers`` puis ``exc.headers`` ; tolère
    toute absence/forme invalide (→ ``None`` → l'appelant calcule un backoff)."""
    for holder in (getattr(exc, "response", None), exc):
        headers = getattr(holder, "headers", None)
        if headers is None or not hasattr(headers, "get"):
            continue
        raw = headers.get("retry-after")
        if raw is None:
            continue
        try:
            seconds = float(raw)
        except (TypeError, ValueError):
            continue
        if seconds >= 0:
            return min(_MAX_BACKOFF, seconds)
    return None


def call_resilient(
    provider: str,
    fn: Callable[[], T],
    *,
    is_retryable: Callable[[BaseException], bool] = http_is_retryable,
    retry_after: Callable[[BaseException], float | None] = http_retry_after,
    attempts: int = _DEFAULT_ATTEMPTS,
    sleep: Callable[[float], None] = time.sleep,
    jitter: Callable[[], float] = _default_jitter,
) -> T:
    """Exécute ``fn`` sous le quota du fournisseur, avec retry borné sur 429/5xx.

    Acquiert ``network_slot(provider)`` **par tentative** (relâché pendant
    l'attente → on ne gèle pas un quota en dormant). Sur erreur retentable et tant
    qu'il reste des tentatives : attend ``Retry-After`` si fourni, sinon un backoff
    exponentiel borné + gigue, puis recommence. Sinon l'exception remonte
    (l'appelant la traduit en ``AdapterStepError`` → unité isolée par le runner).
    ``sleep``/``jitter`` injectables (tests déterministes). **Ne change que le
    *timing*, jamais la valeur renvoyée.**"""
    for attempt in range(attempts):
        delay = 0.0
        with network_slot(provider):
            try:
                return fn()
            except Exception as exc:
                if not is_retryable(exc) or attempt == attempts - 1:
                    raise
                after = retry_after(exc)
                delay = after if after is not None else _backoff(attempt, jitter)
                logger.warning(
                    "[resilience] %s : tentative %d/%d échouée (%s) — "
                    "nouvelle tentative dans %.1f s.",
                    provider,
                    attempt + 1,
                    attempts,
                    type(exc).__name__,
                    delay,
                )
        sleep(delay)  # hors du créneau : on ne retient pas le quota en dormant
    raise AssertionError(  # pragma: no cover — la boucle retourne ou relance avant
        "call_resilient : boucle épuisée sans issue"
    )


__all__ = [
    "call_resilient",
    "http_is_retryable",
    "http_retry_after",
    "network_slot",
]
