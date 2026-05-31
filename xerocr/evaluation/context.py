"""``DocContext`` — sac d'entrées d'une métrique par-document.

Extensible **par ajout de champ** (profil de normalisation, tokens rares,
statistiques de corpus…), chacun introduit **avec son consommateur** — jamais
spéculé. En T1 : la référence (vérité-terrain) et l'hypothèse (sortie candidate),
déjà chargées dans leur représentation (``str`` pour le texte).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DocContext:
    """Entrées d'une métrique pour un document donné."""

    document_id: str
    reference: object
    hypothesis: object


__all__ = ["DocContext"]
