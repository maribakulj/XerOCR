"""Détection runtime de **disponibilité des moteurs** (couche 6).

Alimente l'onglet « Moteurs » : pour chaque kind du socle, dit s'il est
**utilisable ici et maintenant** et *pourquoi pas* le cas échéant. Les sondes
sont **bon marché et sans effet de bord** — on ne lance aucun moteur, on ne
touche pas le réseau : présence d'un binaire (``shutil.which``), d'un SDK
(``importlib.util.find_spec``, **sans importer**), d'une clé d'API (env). Le
**mode public** masque les moteurs *cloud* porteurs de clé (sécurité d'exposition).

Sondes **injectables** → la détection est déterministe en test, indépendante de
l'environnement de CI (où tesseract peut être présent ou non).
"""

from __future__ import annotations

import importlib.util
import os
import shutil
from collections.abc import Callable

from pydantic import BaseModel, ConfigDict

#: Kinds *cloud* (clé API) masqués en mode public.
CLOUD_KINDS = frozenset({"openai"})

BinaryProbe = Callable[[str], str | None]
ModuleProbe = Callable[[str], bool]
EnvProbe = Callable[[str], str | None]


class EngineStatus(BaseModel):
    """État d'un moteur du socle pour l'onglet « Moteurs »."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: str
    label: str
    available: bool
    detail: str


def _module_present(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):  # parent absent / nom dégénéré
        return False


def engine_statuses(
    *,
    public_mode: bool,
    has_binary: BinaryProbe = shutil.which,
    has_module: ModuleProbe = _module_present,
    get_env: EnvProbe = os.environ.get,
) -> tuple[EngineStatus, ...]:
    """État de chaque moteur du socle (ordre stable), selon les sondes fournies."""
    return (
        EngineStatus(
            kind="precomputed",
            label="Pré-calculé",
            available=True,
            detail="intégré (aucune dépendance)",
        ),
        _tesseract_status(has_binary, has_module),
        _openai_status(public_mode, has_module, get_env),
        _ollama_status(has_module),
    )


def _tesseract_status(has_binary: BinaryProbe, has_module: ModuleProbe) -> EngineStatus:
    if has_binary("tesseract") is None:
        detail, ok = "binaire « tesseract » introuvable", False
    elif not has_module("pytesseract"):
        detail, ok = "pytesseract non installé (extra [tesseract])", False
    else:
        detail, ok = "prêt (binaire + pytesseract)", True
    return EngineStatus(
        kind="tesseract", label="Tesseract", available=ok, detail=detail
    )


def _openai_status(
    public_mode: bool, has_module: ModuleProbe, get_env: EnvProbe
) -> EngineStatus:
    if public_mode:
        detail, ok = "moteur cloud désactivé (mode public)", False
    elif not has_module("openai"):
        detail, ok = "SDK openai non installé (extra [openai])", False
    elif not get_env("OPENAI_API_KEY"):
        detail, ok = "clé OPENAI_API_KEY absente", False
    else:
        detail, ok = "prêt (SDK + clé)", True
    return EngineStatus(kind="openai", label="OpenAI", available=ok, detail=detail)


def _ollama_status(has_module: ModuleProbe) -> EngineStatus:
    if not has_module("httpx"):
        detail, ok = "httpx non installé", False
    else:
        detail, ok = "serveur local attendu (non sondé)", True
    return EngineStatus(kind="ollama", label="Ollama", available=ok, detail=detail)


__all__ = ["CLOUD_KINDS", "EngineStatus", "engine_statuses"]
