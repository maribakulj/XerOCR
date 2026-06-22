"""Section détail document : panneaux drill-in (CER/moteur + diff pires lignes)."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.analysis import (
    Analysis,
    DiagnosticsPayload,
    DocumentHallucination,
    DocumentHallucinationPayload,
    DocumentLines,
    DocumentLinesPayload,
    DocumentTexts,
    DocumentTextsPayload,
    HallucinatedBlock,
    PipelineHallucination,
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


def _flag(doc_id: str) -> Analysis:
    """Signale un document (bloc inséré sans appui GT) → il reçoit une fiche
    RICHE (drill-in B) ; les non-signalés n'ont qu'une fiche légère."""
    return Analysis(
        scope="corpus", view="text",
        payload=DocumentHallucinationPayload(documents=(
            DocumentHallucination(document_id=doc_id, pipelines=(
                PipelineHallucination(
                    pipeline="tesseract", anchor_score=0.2, length_ratio=2.0,
                    net_insertion_rate=0.5, gt_words=10, hyp_words=20,
                    is_hallucinating=True,
                    blocks=(HallucinatedBlock(start_token=0, end_token=3, text="a b c"),),
                ),
            )),
        )),
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
    # folio_1 est signalé (fiche riche) ; folio_2 ne l'est pas (fiche légère).
    analyses: tuple[Analysis, ...] = (_flag("folio_1"),)
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
        analyses = (*analyses, Analysis(scope="corpus", view="text", payload=payload))
    return RunResult(
        manifest=manifest,
        pipelines=(
            PipelineResult(pipeline="tesseract", view="text", aggregate=()),
            PipelineResult(pipeline="pero", view="text", aggregate=()),
        ),
        documents=docs,
        analyses=analyses,
    )


def test_rich_template_only_for_flagged_plus_island() -> None:
    # Drill-in B : fiche riche (serveur, <template> inerte) UNIQUEMENT pour les
    # documents signalés (folio_1) → octets bornés ; les autres → fiche légère
    # reconstruite côté client depuis l'îlot. DOM borné (une fiche vivante).
    html = DocumentDetailSection().render(_result(), SectionContext())
    assert html is not None
    assert html.count("<template data-doc=") == 1  # seul folio_1 (signalé)
    assert 'data-doc="0"' in html  # folio_1 = index 0 (≡ ordre galerie)
    assert html.count('class="drill-panel doc-detail"') == 1  # 1 fiche riche serveur
    assert 'class="doc-detail-live"' in html  # conteneur vivant unique (cible clone)
    assert " hidden " not in html.split("doc-detail-live")[0]  # live non caché
    # Îlot compact : TOUS les documents y figurent → atteignables en fiche légère.
    assert 'id="xerocr-doc-data"' in html
    assert '"folio_1"' in html and '"folio_2"' in html


def test_bytes_bounded_island_carries_all_docs_at_scale() -> None:
    # 300 docs, aucun signalé (CER uniforme → pas d'outlier, pas de désaccord) :
    # ZÉRO fiche riche (octets bornés). Tous restent atteignables via l'îlot, où
    # ne figurent que des nombres/identifiants → sortie petite (≠ 300 fiches).
    manifest = RunManifest(
        run_id="r", corpus_name="demo", n_documents=300,
        code_version="1.0", started_at=FIXED, completed_at=FIXED,
    )
    docs = tuple(_doc(f"doc{i:04d}", "tesseract", 0.10) for i in range(300))
    result = RunResult(
        manifest=manifest,
        pipelines=(PipelineResult(pipeline="tesseract", view="text"),),
        documents=docs,
    )
    html = DocumentDetailSection().render(result, SectionContext())
    assert html is not None
    assert html.count("<template data-doc=") == 0  # aucune fiche riche
    assert 'id="xerocr-doc-data"' in html
    assert '"doc0299"' in html  # le 300e doc est dans l'îlot (atteignable)
    assert len(html) < 60_000  # borne d'octets (≠ 300 fiches riches sérialisées)


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
    assert 'class="dd-fac-zoom"' in html  # conteneur zoomable/pan
    assert 'class="dd-fac-img" src="data:image/jpeg;base64,ZZZ"' in html
    assert 'data-zoom="in"' in html and 'data-zoom="reset"' in html  # contrôles zoom
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
    result = base.model_copy(update={"analyses": (
        _flag("folio_1"), Analysis(scope="corpus", view="text", payload=texts),
    )})
    html = DocumentDetailSection().render(result, SectionContext())
    assert html is not None
    assert "page complète" in html  # diff pleine page (≠ pires lignes)
    assert 'class="dd-engine-tabs' in html  # sélecteur de moteur
    assert html.count('class="dd-fulldiff"') == 2  # un bloc par moteur
    assert html.count('class="dd-sbs"') == 2  # GT | sortie côte à côte par moteur
    assert "Vérité terrain" in html and "Sortie ·" in html
    # le diff caractère est marqué (insertion/suppression)
    assert 'class="d-ins"' in html or 'class="d-del"' in html



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
    result = base.model_copy(update={"analyses": (
        _flag("folio_1"), Analysis(scope="corpus", view="text", payload=dl),
    )})
    html = DocumentDetailSection().render(result, SectionContext())
    assert html is not None
    assert 'class="dd-lh"' in html  # distribution par ligne du doc
    assert "dd-lh-bar lh-g" in html and "dd-lh-bar lh-b" in html  # carte thermique
    assert "height:4px" in html and "height:22px" in html  # hauteur ∝ CER (0.0 / 0.5)
    assert html.count('class="dd-ld-row"') == 2  # une distribution par moteur
    assert 'class="dd-pct-row"' in html and "p99" in html  # percentiles CER
    assert "Gini" in html and "CER≥30 %" in html  # badges de distribution



def test_hallucination_block_recentred_on_document() -> None:
    base = _result()
    dh = DocumentHallucinationPayload(
        documents=(
            DocumentHallucination(
                document_id="folio_1",
                pipelines=(
                    PipelineHallucination(
                        pipeline="tesseract",
                        anchor_score=0.20,
                        length_ratio=1.35,
                        net_insertion_rate=0.45,
                        gt_words=36,
                        hyp_words=42,
                        is_hallucinating=True,
                        blocks=(
                            HallucinatedBlock(
                                start_token=0, end_token=5, text="durch beflhuß vom san"
                            ),
                        ),
                    ),
                ),
            ),
        )
    )
    result = base.model_copy(
        update={"analyses": (Analysis(scope="corpus", view="text", payload=dh),)}
    )
    html = DocumentDetailSection().render(result, SectionContext())
    assert html is not None
    assert 'class="dd-hl"' in html  # analyse hallucination du doc
    assert "Ancrage 20 %" in html and "Insertion nette 45 %" in html  # indicateurs
    assert 'class="dd-hl-flag"' in html  # drapeau hallucination détectée
    assert "durch beflhuß vom san" in html  # bloc halluciné affiché


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
    assert "← All documents" in html and "← Tous les documents" not in html
