"""Invariance d'échelle du rapport : les sections par-document produisent une
structure DOM **bornée** — même rendu (compteurs identiques ou plafonnés) que le
corpus porte 6 ou 6000 documents. C'est le cœur de la demande : un seul type de
rapport, pas de troncature conditionnelle ni d'énumération par document.
"""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.analysis import (
    Analysis,
    DocumentImageQuality,
    ImageQualityPayload,
)
from xerocr.evaluation.result import (
    MetricScore,
    PipelineResult,
    RunDocumentResult,
    RunResult,
)
from xerocr.reports._doc_highlights import HIGHLIGHTS_PER_GROUP
from xerocr.reports.section import SectionContext
from xerocr.reports.sections.by_document import DocumentSection
from xerocr.reports.sections.document_detail import DocumentDetailSection
from xerocr.reports.sections.engine_profile import EngineProfileSection
from xerocr.reports.sections.gallery import DocumentGallerySection
from xerocr.reports.sections.image_quality import ImageQualitySection
from xerocr.reports.sections.quality_error import QualityErrorSection

FIXED = datetime(2026, 1, 1, tzinfo=UTC)
_ENGINES = ("tesseract", "pero")


def _build(n_docs: int) -> RunResult:
    """Run synthétique à ``n_docs`` documents (2 moteurs, CER + qualité d'image)."""
    manifest = RunManifest(
        run_id="r", corpus_name="c", n_documents=n_docs, code_version="1.0",
        started_at=FIXED, completed_at=FIXED,
    )
    pipelines = tuple(
        PipelineResult(
            pipeline=e, view="text",
            aggregate=(MetricScore(metric="cer", value=0.2, support=n_docs),),
        )
        for e in _ENGINES
    )
    docs: list[RunDocumentResult] = []
    for i in range(n_docs):
        for j, eng in enumerate(_ENGINES):
            cer = ((i * 7 + j * 13) % 100) / 100.0  # étalé, déterministe
            docs.append(
                RunDocumentResult(
                    document_id=f"doc{i:05d}", pipeline=eng, view="text",
                    scores=(MetricScore(metric="cer", value=cer, support=120),),
                )
            )
    iq = ImageQualityPayload(
        documents=tuple(
            DocumentImageQuality(
                document_id=f"doc{i:05d}", sharpness=0.7, noise=0.1, contrast=0.6,
                rotation_degrees=0.0, quality_score=(i % 100) / 100.0,
                tier="medium",
            )
            for i in range(n_docs)
        ),
        mean_quality=0.5, mean_sharpness=0.7, mean_noise=0.1, mean_contrast=0.6,
        n_good=0, n_medium=n_docs, n_poor=0,
    )
    return RunResult(
        manifest=manifest, pipelines=pipelines, documents=tuple(docs),
        analyses=(Analysis(scope="corpus", view="text", payload=iq),),
    )


_SMALL = _build(6)
_LARGE = _build(3000)
_CTX = SectionContext()


def _count(section: object, marker: str) -> tuple[int, int]:
    small = section.render(_SMALL, _CTX)  # type: ignore[attr-defined]
    large = section.render(_LARGE, _CTX)  # type: ignore[attr-defined]
    assert small is not None and large is not None
    return small.count(marker), large.count(marker)


def test_gallery_cards_bounded() -> None:
    # Cartes = documents notables (≤ 3 groupes × HIGHLIGHTS_PER_GROUP), pas par doc.
    small, large = _count(DocumentGallerySection(), "doc-card")
    assert large <= 3 * HIGHLIGHTS_PER_GROUP
    assert small <= 6  # petit corpus : au plus le nombre de documents


def test_document_detail_panels_bounded() -> None:
    small, large = _count(DocumentDetailSection(), 'class="drill-panel')
    assert large <= 3 * HIGHLIGHTS_PER_GROUP


def test_gallery_and_detail_indices_aligned() -> None:
    # Les ancres #doc-<idx> des cartes doivent matcher les id des fiches (même
    # ensemble notable, même ordre) — sinon le drill-in ouvre la mauvaise fiche.
    gallery = DocumentGallerySection().render(_LARGE, _CTX)
    detail = DocumentDetailSection().render(_LARGE, _CTX)
    assert gallery is not None and detail is not None
    import re

    card_idx = set(re.findall(r'href="#doc-(\d+)"', gallery))
    panel_idx = set(re.findall(r'id="doc-(\d+)"', detail))
    assert card_idx and card_idx == panel_idx


def test_by_document_rows_bounded_single_distribution() -> None:
    small_rows, large_rows = _count(DocumentSection(), "<tr>")
    assert large_rows <= 3 * HIGHLIGHTS_PER_GROUP + 1  # +1 = ligne d'en-tête
    # une seule distribution (histogramme) quel que soit N
    small_h, large_h = _count(DocumentSection(), "bars-svg")
    assert small_h == 1 and large_h == 1


def test_image_quality_table_rows_bounded() -> None:
    # Table = pires scans (≤ HIGHLIGHTS_PER_GROUP) ; histogramme couvre tout.
    small, large = _count(ImageQualitySection(), "<tr>")
    assert large <= HIGHLIGHTS_PER_GROUP + 1  # +1 = ligne d'en-tête
    assert _count(ImageQualitySection(), "bars-svg") == (1, 1)


def test_quality_error_bubbles_bounded() -> None:
    _small, large = _count(QualityErrorSection(), 'class="bubble-dot"')
    assert large <= 24 * 24  # densité binnée, pas une bulle par couple


def test_engine_profile_histogram_bars_bounded() -> None:
    # Le profil moteur trace un histogramme (classes fixes), pas une barre/doc.
    small = EngineProfileSection().render(_SMALL, _CTX)
    large = EngineProfileSection().render(_LARGE, _CTX)
    assert small is not None and large is not None
    # ≤ 24 classes × nb de fichiers <rect> par moteur ; borné, indépendant de N.
    assert large.count("<rect") == small.count("<rect") or large.count("<rect") <= (
        24 * len(_ENGINES) + 4
    )
