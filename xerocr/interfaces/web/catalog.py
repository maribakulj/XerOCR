"""Catalogue des rapports servis par la vitrine (couche 8).

Un rapport = un ``RunResult`` **sauvé** (JSON, via ``run --json``) déposé dans un
dossier. La vitrine les **liste** et les **rend en HTML à la demande** : le rendu
est déterministe (§12), donc recalculable sans état serveur, et le format unique
``RunResult`` reste la source de vérité (pas de HTML pré-figé).

Tout accès passe par ``validated_path`` (couche 6) : un identifiant ne peut pas
sortir du dossier (défense path-traversal, invariant §12).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from xerocr.app.security import validated_path


def available_reports(reports_dir: Path) -> list[str]:
    """Identifiants (stems ``.json``) des rapports disponibles, **triés**.

    Dossier absent → ``[]`` (le Space peut démarrer avant qu'un rapport existe).
    """
    if not reports_dir.is_dir():
        return []
    return sorted(path.stem for path in reports_dir.glob("*.json"))


def resolve_report(reports_dir: Path, name: str) -> Path:
    """Chemin sûr de ``<name>.json``, **confiné** à ``reports_dir``.

    Lève ``PathSecurityError`` si ``name`` tente de sortir du dossier **ou**
    n'existe pas (``must_exist``) — le routeur traduit les deux en 404, sans
    distinguer (pas de fuite d'information).
    """
    return validated_path(f"{name}.json", reports_dir, must_exist=True)


def seed_reports(src: Path, dst: Path) -> None:
    """Copie les rapports *bakés* (``src``) dans le dossier inscriptible ``dst``.

    Permet à la vitrine de servir, depuis un **seul** dossier inscriptible, à la
    fois les rapports livrés dans l'image (graine) et ceux produits au runtime.
    Idempotent et best-effort : un rapport déjà présent n'est jamais réécrit (un
    run produit prime sur la graine homonyme) ; ``src`` absent → no-op.
    """
    if src == dst or not src.is_dir():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for path in src.glob("*.json"):
        target = dst / path.name
        if not target.exists():
            shutil.copy2(path, target)


__all__ = ["available_reports", "resolve_report", "seed_reports"]
