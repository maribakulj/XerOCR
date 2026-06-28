"""Chemins de sortie dans le workspace (couche 5, partagé par les écrivains).

Les adapters qui **produisent** un artefact (OCR, post-correction LLM) y déposent
un fichier. Le ``stem`` dérivé du ``document_id`` est **injectif** et sans
séparateur de chemin : encodage type URL (``quote``), **réversible** donc
injectif, qui neutralise ``/`` (→ ``%2F``) et l'octet nul (→ ``%00``). Deux ids
distincts ne peuvent jamais produire le même nom de fichier (et donc s'écraser) —
y compris les cas limites ``a/_b`` vs ``a_/b`` qu'un simple échappement maison
collisionnerait. Les ids courants (alphanumériques) restent lisibles.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote


def safe_document_stem(document_id: str) -> str:
    """``document_id`` → composant de nom de fichier **injectif** et sans ``/``."""
    return quote(document_id, safe="")


def workspace_artifact_path(
    workspace_uri: str, document_id: str, label: str, suffix: str
) -> Path:
    """Chemin ``<workspace>/<stem>.<label>.<suffix>`` (``stem`` injectif)."""
    stem = safe_document_stem(document_id)
    return Path(workspace_uri) / f"{stem}.{label}.{suffix}"


__all__ = ["safe_document_stem", "workspace_artifact_path"]
