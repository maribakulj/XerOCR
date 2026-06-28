"""Sécurité des chemins (couche 6) — invariant produit §12.

``validated_path`` est le **garde-fou central** contre la traversée de
répertoires : tout chemin venant d'une entrée utilisateur (corpus, sortie) passe
par lui. La couche 8 (web) réutilisera ce **même** helper — la sécurité chemin
n'est pas un détail web.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from cinoc.domain.errors import CinocError


class PathSecurityError(CinocError):
    """Un chemin utilisateur sort de la zone autorisée (path traversal)."""


def safe_stem(value: str, *, suffix: str = "", fallback: str = "x") -> str:
    """Composant de chemin **sûr** dérivé d'une chaîne (anti path-traversal).

    Slug lisible (caractères sûrs sur tous les OS : ``A-Za-z0-9._-``) + empreinte
    SHA-256 courte de la valeur **brute** → jamais de collision même si deux
    valeurs se réduisent au même slug. ``suffix`` distingue des variantes (vignette
    vs fac-similé) ; ``fallback`` remplace un slug vide (valeur tout-symboles).

    Source unique du « nom de fichier sûr » (invariant produit §12) — réutilisée
    par ``alto_store`` et ``report_images``.
    """
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or fallback
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
    return f"{cleaned}-{digest}{suffix}"


def validated_path(user_path: str, base: Path, *, must_exist: bool = False) -> Path:
    """Résout ``user_path`` (sous ``base``) et garantit qu'il y reste confiné.

    ``Path.resolve()`` écrase ``..``, les liens symboliques et le relatif ; on
    vérifie ensuite que le résultat est bien sous ``base``. Un chemin absolu
    n'est accepté que s'il tombe lui-même sous ``base``.
    """
    if not user_path or not user_path.strip():
        raise PathSecurityError("chemin vide.")
    if "\x00" in user_path:
        raise PathSecurityError("chemin contient un octet nul.")
    base_resolved = base.expanduser().resolve()
    candidate = Path(user_path)
    # ``target`` est toujours absolu (candidat absolu, sinon préfixé par ``base``
    # déjà résolu) → pas de ``~`` en tête : aucun ``expanduser`` à refaire ici.
    target = candidate if candidate.is_absolute() else base_resolved / candidate
    try:
        resolved = target.resolve()
    except (OSError, RuntimeError) as exc:
        raise PathSecurityError(
            f"chemin invalide : {user_path!r} ({exc})."
        ) from exc
    if not resolved.is_relative_to(base_resolved):
        raise PathSecurityError(
            f"chemin hors de la zone autorisée : {user_path!r}."
        )
    if must_exist and not resolved.exists():
        raise PathSecurityError(f"chemin inexistant : {user_path!r}.")
    return resolved


__all__ = ["PathSecurityError", "safe_stem", "validated_path"]
