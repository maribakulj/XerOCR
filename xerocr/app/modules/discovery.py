"""Découverte de modules de pipeline **tiers** via entry-points (couche 6).

Le **seul** point d'extension tiers du produit (CLAUDE.md §3) : un paquet pip
déclare ::

    [project.entry-points."xerocr.modules"]
    yolo_seg = "mon_paquet.seg:build_yolo"

Chaque entrée nomme un ``kind`` (``yolo_seg``) et charge un ``ModuleBuilder``
(``build_yolo``), enregistré dans le ``ModuleRegistry`` runtime — **exactement**
comme le socle (``register_default_modules``), même ``Module`` Protocol, seule la
source diffère. Un YOLO de segmentation se branche ainsi **sans forker** : c'est
un ``Module`` ``IMAGE → LAYOUT`` que le fan-out consomme comme les autres.

**Sécurité** : le code tiers s'exécute **in-process**. En **mode public** la
découverte est **désactivée (fail-closed)** — jamais de chargement de code
arbitraire sur un serveur exposé. Un plugin défectueux est **journalisé et
ignoré**, il n'abat pas le démarrage.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from typing import Protocol

from xerocr.app.modules.registry import ModuleRegistry

logger = logging.getLogger(__name__)

#: Groupe d'entry-points scanné pour les modules de pipeline tiers.
ENTRY_POINT_GROUP = "xerocr.modules"


class _EntryPoint(Protocol):
    """Forme minimale consommée d'un entry-point (``importlib.metadata``)."""

    @property
    def name(self) -> str: ...

    def load(self) -> object: ...


#: Fournit les entry-points du groupe — injectable pour les tests.
EntryPointsLoader = Callable[[], Iterable[_EntryPoint]]


def _default_entry_points() -> Iterable[_EntryPoint]:
    from importlib.metadata import entry_points

    return entry_points(group=ENTRY_POINT_GROUP)


def discover_plugins(
    registry: ModuleRegistry,
    *,
    enabled: bool,
    entry_points_loader: EntryPointsLoader | None = None,
) -> tuple[str, ...]:
    """Enregistre les builders tiers du groupe ``xerocr.modules`` dans ``registry``.

    Renvoie les ``kind`` découverts (ordre de découverte). ``enabled=False``
    (mode public) → aucune découverte. Un entry-point qui échoue à charger, ou
    qui ne fournit pas un builder appelable, est **journalisé et sauté**.
    """
    if not enabled:
        logger.info("[plugins] découverte désactivée (mode public, fail-closed)")
        return ()
    loader = entry_points_loader or _default_entry_points
    discovered: list[str] = []
    for entry_point in loader():
        try:
            builder = entry_point.load()
        except Exception as exc:  # le code tiers peut lever n'importe quoi
            logger.warning(
                "[plugins] entry-point %r : chargement échoué, ignoré : %s",
                entry_point.name,
                exc,
            )
            continue
        if not callable(builder):
            logger.warning(
                "[plugins] entry-point %r : %r n'est pas un builder appelable, ignoré",
                entry_point.name,
                type(builder).__name__,
            )
            continue
        registry.register_builder(entry_point.name, builder)
        discovered.append(entry_point.name)
        logger.info("[plugins] module tiers enregistré : %r", entry_point.name)
    return tuple(discovered)


__all__ = ["ENTRY_POINT_GROUP", "EntryPointsLoader", "discover_plugins"]
