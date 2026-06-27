"""Section documents : **galerie d'entrée** + bascule ⊞ Grille / ≡ Liste (couche 7).

La galerie (cartes par document) est l'**entrée** de la vue ; la table dense
``by_document`` devient le mode **Liste** derrière un toggle. Compose les deux
rendus existants (réutilisation, pas de duplication). Enrichissement progressif :
sans JS, la grille (entrée) s'affiche, ``report.js`` bascule vers la liste.
"""

from __future__ import annotations

from cinoc.evaluation.result import RunResult
from cinoc.reports.html import localized
from cinoc.reports.section import Html, SectionContext
from cinoc.reports.sections.by_document import DocumentSection
from cinoc.reports.sections.gallery import DocumentGallerySection


class DocumentsSection:
    """Vue documents : galerie (grille, entrée) ⇄ table (liste), via un toggle."""

    name = "documents"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        # Vue **maître** seule (galerie ⇄ liste). Les fiches détail document
        # vivent dans une section sœur ``document_details`` (conteneur ``.tab-detail``
        # échangé au clic par le routeur) — pas dans le flux maître.
        grid = DocumentGallerySection().render(result, ctx)
        lst = DocumentSection().render(result, ctx)
        if grid is None and lst is None:
            return None
        affichage = localized(ctx.lang, "Affichage", "Display")
        grid_label = localized(ctx.lang, "Grille", "Grid")
        list_label = localized(ctx.lang, "Liste", "List")
        toggle = (
            f'<div class="view-toggle" role="group" aria-label="{affichage}">'
            '<button type="button" class="vt-btn on" data-view="grid" '
            f'aria-pressed="true">⊞ {grid_label}</button>'
            '<button type="button" class="vt-btn" data-view="list" '
            f'aria-pressed="false">≡ {list_label}</button></div>'
        )
        return Html(
            f"{toggle}"
            f'<div class="doc-view" data-view="grid">{grid or ""}</div>'
            f'<div class="doc-view" data-view="list" hidden>{lst or ""}</div>'
        )


__all__ = ["DocumentsSection"]
