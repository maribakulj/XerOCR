"""Section détail document : panneaux drill-in (CER/moteur + diff pires lignes)."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.analysis import (
    Analysis,
    DiagnosticsPayload,
    DocumentTexts,
    DocumentTextsPayload,
    WorstLine,
)
from xerocr.evaluation.result import (
    MetricScore,
    PipelineResult,
    RunDocumentResult,
    RunResult,
)
from xerocr.reports.section import SectionContext
from xerocr.reports.sections.document_detail import DocumentDetailSection

FIXED = datetime(2026, 1, 1, tzinfo=UTC)


def _doc(doc_id: str, pipeline: str, cer: float) -> RunDocumentResult:
    return RunDocumentResult(
        document_id=doc_id, pipeline=pipeline, view="text",
        scores=(MetricScore(metric="cer", value=cer, support=1),),
    )


def _result(*, with_worst: bool = False) -> RunResult:
    manifest = RunManifest(
        run_id="r", corpus_name="demo", n_documents=2,
        code_version="1.0", started_at=FIXED, completed_at=FIXED,
    )
    docs = (
        _doc("folio_1", "tesseract", 0.20), _doc("folio_1", "pero", 0.10),
        _doc("folio_2", "tesseract", 0.30),
    )
    analyses = ()
    if with_worst:
        payload = DiagnosticsPayload(
            metric="cer",
            worst_lines=(
                WorstLine(
                    pipeline="tesseract", document_id="folio_1", line_index=3,
                    cer=0.5, reference="le chat", hypothesis="le chien",
                ),
            ),
        )
        analyses = (Analysis(scope="corpus", view="text", payload=payload),)
    return RunResult(
        manifest=manifest,
        pipelines=(
            PipelineResult(pipeline="tesseract", view="text", aggregate=()),
            PipelineResult(pipeline="pero", view="text", aggregate=()),
        ),
        documents=docs,
        analyses=analyses,
    )


def test_one_hidden_panel_per_document_with_anchor() -> None:
    html = DocumentDetailSection().render(_result(), SectionContext())
    assert html is not None
    assert html.count('class="drill-panel doc-detail"') == 2  # un par document
    assert 'id="doc-0"' in html and 'id="doc-1"' in html  # ancres (≡ ordre galerie)
    assert "← retour à la galerie" in html


def test_panel_shows_cer_per_engine() -> None:
    html = DocumentDetailSection().render(_result(), SectionContext())
    assert html is not None
    assert "CER par moteur" in html
    assert "20.0 %" in html and "10.0 %" in html  # folio_1 : tesseract / pero


def test_worst_lines_diff_when_present() -> None:
    html = DocumentDetailSection().render(_result(with_worst=True), SectionContext())
    assert html is not None
    assert "Pires lignes" in html
    assert 'class="diff"' in html  # diff caractère réutilisé (text_diff)
    assert "ligne 3" in html


def test_facsimile_shown_when_provided() -> None:
    ctx = SectionContext(facsimiles={"folio_1": "data:image/jpeg;base64,ZZZ"})
    html = DocumentDetailSection().render(_result(), ctx)
    assert html is not None
    assert 'class="dd-cols"' in html  # 2 colonnes (fac-similé | CER/diff)
    assert 'class="dd-fac-img" src="data:image/jpeg;base64,ZZZ"' in html
    # un doc sans fac-similé reste en pleine largeur (pas d'image vide)
    plain = DocumentDetailSection().render(_result(), SectionContext())
    assert plain is not None and "dd-fac-img" not in plain


def test_full_page_diff_with_engine_selector() -> None:
    base = _result()
    texts = DocumentTextsPayload(
        documents=(
            DocumentTexts(
                document_id="folio_1",
                reference="le chat noir",
                hypotheses=(("pero", "le chat noir"), ("tesseract", "le chien noir")),
            ),
        )
    )
    result = base.model_copy(
        update={"analyses": (Analysis(scope="corpus", view="text", payload=texts),)}
    )
    html = DocumentDetailSection().render(result, SectionContext())
    assert html is not None
    assert "page complète" in html  # diff pleine page (≠ pires lignes)
    assert 'class="dd-engine-tabs' in html  # sélecteur de moteur
    assert html.count('class="dd-fulldiff"') == 2  # un bloc par moteur
    assert "Vérité terrain" in html and "Sortie ·" in html
    # le diff caractère est marqué (insertion/suppression)
    assert 'class="d-ins"' in html or 'class="d-del"' in html


def test_none_without_documents() -> None:
    manifest = RunManifest(
        run_id="r", corpus_name="demo", n_documents=0,
        code_version="1.0", started_at=FIXED, completed_at=FIXED,
    )
    empty = RunResult(manifest=manifest)
    assert DocumentDetailSection().render(empty, SectionContext()) is None


def test_renders_english_labels() -> None:
    html = DocumentDetailSection().render(
        _result(with_worst=True), SectionContext(lang="en")
    )
    assert html is not None
    assert "CER per engine" in html and "CER par moteur" not in html
    assert "Worst lines" in html and "Pires lignes" not in html
    assert "← back to gallery" in html and "← retour à la galerie" not in html
