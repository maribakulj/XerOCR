"""Section documents : **galerie d'entrée** + bascule ⊞ Grille / ≡ Liste (couche 7).

La galerie (cartes par document) est l'**entrée** de la vue ; la table dense
``by_document`` devient le mode **Liste** derrière un toggle. Compose les deux
rendus existants (réutilisation, pas de duplication). Enrichissement progressif :
sans JS, la grille (entrée) s'affiche, ``report.js`` bascule vers la liste.
"""

from __future__ import annotations

from xerocr.evaluation.result import RunResult
from xerocr.reports.section import Html, SectionContext
from xerocr.reports.sections.by_document import DocumentSection
from xerocr.reports.sections.gallery import DocumentGallerySection


class DocumentsSection:
    """Vue documents : galerie (grille, entrée) ⇄ table (liste), via un toggle."""

    name = "documents"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        grid = DocumentGallerySection().render(result, ctx)
        lst = DocumentSection().render(result, ctx)
        if grid is None and lst is None:
            return None
        toggle = (
            '<div class="view-toggle" role="group" aria-label="Affichage">'
            '<button type="button" class="vt-btn on" data-view="grid" '
            'aria-pressed="true">⊞ Grille</button>'
            '<button type="button" class="vt-btn" data-view="list" '
            'aria-pressed="false">≡ Liste</button></div>'
        )
        return Html(
            f"{toggle}"
            f'<div class="doc-view" data-view="grid">{grid or ""}</div>'
            f'<div class="doc-view" data-view="list" hidden>{lst or ""}</div>'
        )


__all__ = ["DocumentsSection"]
