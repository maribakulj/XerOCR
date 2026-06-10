"""Détection runtime de **disponibilité des moteurs** (couche 6).

Alimente l'onglet « Moteurs » : pour chaque kind du socle, dit s'il est
**utilisable ici et maintenant** et *pourquoi pas* le cas échéant. Les sondes
sont **bon marché et sans effet de bord** — on ne lance aucun moteur, on ne
touche pas le réseau : présence d'un binaire (``shutil.which``), d'un SDK
(``importlib.util.find_spec``, **sans importer**), d'une clé d'API (env). Un
moteur cloud est dispo dès que **SDK + clé** sont là (« clé posée → ça marche »),
sans masquage par mode public — la sécurité d'un Space exposé tient à sa visibilité.

Sondes **injectables** → la détection est déterministe en test, indépendante de
l'environnement de CI (où tesseract peut être présent ou non).
"""

from __future__ import annotations

import importlib.util
import os
import shutil
from collections.abc import Callable

from pydantic import BaseModel, ConfigDict

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


#: Fournit l'état courant des moteurs (capturé par ``create_app`` avec le mode).
#: Source unique du contrat ; les routeurs (couche 8) l'importent — pas de copie.
StatusProvider = Callable[[], tuple[EngineStatus, ...]]


def _module_present(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):  # parent absent / nom dégénéré
        return False


def engine_statuses(
    *,
    has_binary: BinaryProbe = shutil.which,
    has_module: ModuleProbe = _module_present,
    get_env: EnvProbe = os.environ.get,
) -> tuple[EngineStatus, ...]:
    """État de chaque moteur du socle (ordre stable), selon les sondes fournies.

    Un moteur cloud (OpenAI/Anthropic/Mistral) est disponible **dès que son SDK et
    sa clé sont présents** — indépendamment du mode public (« clé posée → ça
    marche »). La protection d'un Space exposé relève de sa **visibilité** (privé)
    et de la présence/absence de la clé, pas d'un masquage côté appli.
    """
    return (
        EngineStatus(
            kind="precomputed",
            label="Pré-calculé",
            available=True,
            detail="intégré (aucune dépendance)",
        ),
        _tesseract_status(has_binary, has_module),
        _kraken_status(has_module),
        _mistral_ocr_status(has_module, get_env),
        _openai_status(has_module, get_env),
        _anthropic_status(has_module, get_env),
        _mistral_status(has_module, get_env),
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


def _kraken_status(has_module: ModuleProbe) -> EngineStatus:
    if not has_module("kraken"):
        detail, ok = "SDK kraken non installé (extra [kraken])", False
    else:
        detail, ok = "prêt (SDK ; fournir un modèle .mlmodel au lancement)", True
    return EngineStatus(
        kind="kraken", label="Kraken (HTR)", available=ok, detail=detail
    )


def _mistral_ocr_status(has_module: ModuleProbe, get_env: EnvProbe) -> EngineStatus:
    if not has_module("mistralai"):
        detail, ok = "SDK mistralai non installé (extra [mistral])", False
    elif not get_env("MISTRAL_API_KEY"):
        detail, ok = "clé MISTRAL_API_KEY absente", False
    else:
        detail, ok = "prêt (SDK + clé)", True
    return EngineStatus(
        kind="mistral_ocr", label="Mistral OCR", available=ok, detail=detail
    )


def _openai_status(has_module: ModuleProbe, get_env: EnvProbe) -> EngineStatus:
    if not has_module("openai"):
        detail, ok = "SDK openai non installé (extra [openai])", False
    elif not get_env("OPENAI_API_KEY"):
        detail, ok = "clé OPENAI_API_KEY absente", False
    else:
        detail, ok = "prêt (SDK + clé)", True
    return EngineStatus(kind="openai", label="OpenAI", available=ok, detail=detail)


def _anthropic_status(has_module: ModuleProbe, get_env: EnvProbe) -> EngineStatus:
    if not has_module("anthropic"):
        detail, ok = "SDK anthropic non installé (extra [anthropic])", False
    elif not get_env("ANTHROPIC_API_KEY"):
        detail, ok = "clé ANTHROPIC_API_KEY absente", False
    else:
        detail, ok = "prêt (SDK + clé)", True
    return EngineStatus(
        kind="anthropic", label="Anthropic", available=ok, detail=detail
    )


def _mistral_status(has_module: ModuleProbe, get_env: EnvProbe) -> EngineStatus:
    if not has_module("mistralai"):
        detail, ok = "SDK mistralai non installé (extra [mistral])", False
    elif not get_env("MISTRAL_API_KEY"):
        detail, ok = "clé MISTRAL_API_KEY absente", False
    else:
        detail, ok = "prêt (SDK + clé)", True
    return EngineStatus(kind="mistral", label="Mistral", available=ok, detail=detail)


def _ollama_status(has_module: ModuleProbe) -> EngineStatus:
    if not has_module("httpx"):
        detail, ok = "httpx non installé", False
    else:
        detail, ok = "serveur local attendu (non sondé)", True
    return EngineStatus(kind="ollama", label="Ollama", available=ok, detail=detail)


def segmenter_statuses(
    *, has_module: ModuleProbe = _module_present
) -> tuple[EngineStatus, ...]:
    """Disponibilité des **segmenteurs** de mise en page du socle (PP-DocLayout).

    Catégorie **distincte** des moteurs de transcription : un segmenteur produit
    un ``LAYOUT`` (géométrie), pas du texte — il n'apparaît donc pas dans le
    ``<select>`` moteur du lanceur OCR. **Jamais masqué en mode public** : un
    segmenteur du socle tourne en **local** (poids, pas de clé d'API) → comme
    ``tesseract``, pas comme un moteur cloud.
    """
    if has_module("paddlex"):
        detail, ok = "prêt (PaddleX installé)", True
    else:
        detail, ok = "PaddleX non installé (extra [segment])", False
    return (
        EngineStatus(
            kind="pp_doclayout", label="PP-DocLayout", available=ok, detail=detail
        ),
    )


def installed_ollama_models() -> tuple[str, ...]:
    """Modèles **réellement installés** sur le serveur ollama local (commodité UI).

    Best-effort : serveur injoignable / extra absent → ``()`` (l'UI retombe sur la
    saisie libre). Sert à proposer un **menu déroulant** des modèles disponibles
    au lieu d'une saisie à l'aveugle. Import local : ne charge ``httpx`` que si on
    interroge réellement le serveur.
    """
    from xerocr.adapters.llm.ollama import list_installed_models

    return list_installed_models()


def installed_mistral_models() -> tuple[str, ...]:
    """Modèles Mistral disponibles pour la clé courante (menu déroulant, UI).

    Best-effort : clé/SDK absent → ``()`` (saisie libre). Rien de hardcodé : la
    liste vient de l'API Mistral. Import local (ne charge le SDK qu'au besoin).
    """
    from xerocr.adapters.llm.mistral import list_mistral_models

    return list_mistral_models()


__all__ = [
    "EngineStatus",
    "StatusProvider",
    "engine_statuses",
    "segmenter_statuses",
]
