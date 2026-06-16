"""Section détail document : panneaux drill-in (CER/moteur + diff pires lignes)."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.analysis import (
    Analysis,
    DiagnosticsPayload,
    DocumentImageQuality,
    DocumentLines,
    DocumentLinesPayload,
    DocumentTaxonomy,
    DocumentTaxonomyPayload,
    DocumentTexts,
    DocumentTextsPayload,
    ImageQualityPayload,
    PipelineTaxonomy,
    TaxonomyCount,
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
    assert 'class="dd-fac-top"' in html  # fac-similé en haut (pleine largeur)
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
    assert html.count('class="dd-sbs"') == 2  # GT | sortie côte à côte par moteur
    assert "Vérité terrain" in html and "Sortie ·" in html
    # le diff caractère est marqué (insertion/suppression)
    assert 'class="d-ins"' in html or 'class="d-del"' in html


def test_image_quality_block_recentred_on_document() -> None:
    base = _result()
    iq = ImageQualityPayload(
        documents=(
            DocumentImageQuality(
                document_id="folio_1", sharpness=0.72, noise=0.10, contrast=0.60,
                rotation_degrees=-1.3, quality_score=0.68, tier="medium",
            ),
        ),
        mean_quality=0.68, mean_sharpness=0.72, mean_noise=0.10, mean_contrast=0.60,
        n_good=0, n_medium=1, n_poor=0,
    )
    result = base.model_copy(
        update={"analyses": (Analysis(scope="corpus", view="text", payload=iq),)}
    )
    html = DocumentDetailSection().render(result, SectionContext())
    assert html is not None
    assert 'class="dd-iq"' in html  # bloc qualité d'image du doc
    assert "Netteté" in html and "dd-iq-bar" in html  # barres mesurées
    assert "-1.3°" in html  # inclinaison de CE doc
    # un doc sans mesure (folio_2) ne porte pas le bloc (dégradé propre)
    assert html.count('class="dd-iq"') == 1


def test_line_heatmap_recentred_on_document() -> None:
    base = _result()
    dl = DocumentLinesPayload(
        documents=(
            DocumentLines(
                document_id="folio_1",
                pipelines=(("tesseract", (0.0, 0.20, 0.5)), ("pero", (0.0, 0.0, 0.1))),
            ),
        )
    )
    result = base.model_copy(
        update={"analyses": (Analysis(scope="corpus", view="text", payload=dl),)}
    )
    html = DocumentDetailSection().render(result, SectionContext())
    assert html is not None
    assert 'class="dd-lh"' in html  # histogramme CER par ligne du doc
    assert "dd-lh-bar lh-g" in html and "dd-lh-bar lh-b" in html  # barres colorées
    assert "height:4px" in html and "height:22px" in html  # hauteur ∝ CER (0.0 / 0.5)
    assert html.count('class="dd-lh-row"') == 2  # un histogramme par moteur


def test_image_quality_stays_last_below_line_heatmap() -> None:
    base = _result()
    dl = DocumentLinesPayload(
        documents=(
            DocumentLines(document_id="folio_1", pipelines=(("tesseract", (0.1,)),)),
        )
    )
    iq = ImageQualityPayload(
        documents=(
            DocumentImageQuality(
                document_id="folio_1", sharpness=0.7, noise=0.1, contrast=0.6,
                rotation_degrees=0.0, quality_score=0.6, tier="medium",
            ),
        ),
        mean_quality=0.6, mean_sharpness=0.7, mean_noise=0.1, mean_contrast=0.6,
        n_good=0, n_medium=1, n_poor=0,
    )
    result = base.model_copy(
        update={
            "analyses": (
                Analysis(scope="corpus", view="text", payload=dl),
                Analysis(scope="corpus", view="text", payload=iq),
            )
        }
    )
    html = DocumentDetailSection().render(result, SectionContext())
    assert html is not None
    # qualité d'image (dd-iq) APRÈS la heatmap (dd-lh) — graphique image en dernier
    assert html.index('class="dd-lh"') < html.index('class="dd-iq"')


def test_error_profile_recentred_on_document() -> None:
    base = _result()
    dt = DocumentTaxonomyPayload(
        classes=("diacritic", "case"),
        documents=(
            DocumentTaxonomy(
                document_id="folio_1",
                pipelines=(
                    PipelineTaxonomy(
                        pipeline="tesseract",
                        total_errors=5,
                        counts=(
                            TaxonomyCount(label="diacritic", count=3),
                            TaxonomyCount(label="case", count=2),
                        ),
                    ),
                ),
            ),
        ),
    )
    result = base.model_copy(
        update={"analyses": (Analysis(scope="corpus", view="text", payload=dt),)}
    )
    html = DocumentDetailSection().render(result, SectionContext())
    assert html is not None
    assert 'class="dd-tx"' in html  # profil d'erreurs du doc
    assert 'class="dd-tx-bar"' in html and "width:60.0%" in html  # diacritic 3/5
    assert "diacritiques" in html  # libellé FR de la classe


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
