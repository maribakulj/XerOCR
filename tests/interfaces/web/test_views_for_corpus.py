"""``_views_for_corpus`` : la sélection des vues d'évaluation d'après les types
de GT présents dans le corpus (consommateur réel de ``REFERENCE_TEXT``, Lot C).

GT manuelle ``RAW_TEXT`` → vue ``text`` ; référence ``REFERENCE_TEXT`` (OCR
Gallica) → vue *référence* distincte (étiquetée dans son nom) ; aucune GT → vue
``text`` par défaut (run OCR-able, non scoré).
"""

from __future__ import annotations

from xerocr.app.run_planning import _views_for_corpus
from xerocr.domain.artifacts import ArtifactType
from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.documents import DocumentRef, GroundTruthRef


def _corpus(*gt_types: ArtifactType) -> CorpusSpec:
    gts = tuple(GroundTruthRef(type=t, uri=f"/tmp/{t.value}.txt") for t in gt_types)
    doc = DocumentRef(id="d1", image_uri="/tmp/a.png", ground_truths=gts)
    return CorpusSpec(name="c", documents=(doc,))


def test_manual_gt_yields_text_view_only() -> None:
    views = _views_for_corpus(_corpus(ArtifactType.RAW_TEXT))
    assert [v.name for v in views] == ["text"]


def test_reference_text_yields_distinct_reference_view() -> None:
    views = _views_for_corpus(_corpus(ArtifactType.REFERENCE_TEXT))
    assert len(views) == 1
    view = views[0]
    # nom auto-documenté (le rapport l'affiche tel quel) + projection opt-in
    assert "vérité-terrain" in view.name
    spec = view.projection_for(ArtifactType.REFERENCE_TEXT)
    assert spec is not None and spec.target_type == ArtifactType.RAW_TEXT


def test_both_gt_types_yield_both_views() -> None:
    views = _views_for_corpus(
        _corpus(ArtifactType.RAW_TEXT, ArtifactType.REFERENCE_TEXT)
    )
    names = [v.name for v in views]
    assert names[0] == "text"
    assert any("vérité-terrain" in n for n in names)


def test_no_gt_falls_back_to_text_view() -> None:
    views = _views_for_corpus(_corpus())
    assert [v.name for v in views] == ["text"]
