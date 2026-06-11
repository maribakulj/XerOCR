"""Contrat unique d'une **section** de rapport (couche 7).

Une seule signature : ``render(RunResult, SectionContext) -> Html | None``. La
section consomme le ``RunResult`` **directement** (pas de data-layer qui
ré-agrège) et déclare ses ``requires`` (clés de métriques nécessaires) ; le
renderer saute une section dont les besoins ne sont pas couverts (« no-orphan
section↔métrique »). ``None`` = rien à afficher.

``Html`` est un ``NewType`` sur ``str`` : il **signale du HTML déjà sûr** (les
données utilisateur sont échappées à la construction) — la frontière anti-XSS.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import NewType, Protocol, runtime_checkable

from xerocr.evaluation.result import RunResult

#: Fragment HTML déjà échappé / de confiance.
Html = NewType("Html", str)


@dataclass(frozen=True)
class SectionContext:
    """Contexte de rendu (extensible : langue, vignettes…)."""

    title: str = "XerOCR"
    lang: str = "fr"
    #: ``{document_id: data-URI}`` des vignettes résolues (intrant de rendu,
    #: calculé hors résultat ; vide → aperçu synthétique). Cf. `app.report_images`.
    images: Mapping[str, str] = field(default_factory=dict)


@runtime_checkable
class Section(Protocol):
    """Brique de rapport typée, qui lit un ``RunResult``."""

    @property
    def name(self) -> str: ...

    @property
    def requires(self) -> tuple[str, ...]: ...

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None: ...


__all__ = ["Html", "Section", "SectionContext"]
