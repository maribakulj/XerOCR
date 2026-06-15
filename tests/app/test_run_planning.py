"""``plan_benchmark_run`` : N concurrents → un ``RunSpec`` (formes de pipeline,
exécution multi-concurrent en un seul run, refus exhaustif)."""

from __future__ import annotations

from pathlib import Path

import pytest

from xerocr.adapters.llm._base import LLMCompletion
from xerocr.app import run
from xerocr.app.engines import EngineStatus
from xerocr.app.modules.registry import ModuleRegistry, register_default_modules
from xerocr.app.run_planning import (
    DEFAULT_METRIC_PROFILE,
    METRIC_PROFILES,
    Competitor,
    RunPlanningError,
    benchmark_engine_catalog,
    metric_profile_catalog,
    plan_benchmark_run,
)
from xerocr.domain.artifacts import ArtifactType
from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.documents import DocumentRef, GroundTruthRef
from xerocr.domain.pipeline import INITIAL_STEP_ID
from xerocr.evaluation.registry import MetricRegistry, register_default_metrics


def _corpus(tmp_path: Path) -> CorpusSpec:
    (tmp_path / "d.gt.txt").write_text("alpha", encoding="utf-8")
    return CorpusSpec(
        name="c",
        documents=(
            DocumentRef(
                id="d",
                image_uri=str(tmp_path / "d.png"),
                ground_truths=(
                    GroundTruthRef(
                        type=ArtifactType.RAW_TEXT, uri=str(tmp_path / "d.gt.txt")
                    ),
                ),
            ),
        ),
    )


def _registry() -> ModuleRegistry:
    registry = ModuleRegistry()
    register_default_modules(registry)
    return registry


def test_empty_competitors_refused(tmp_path: Path) -> None:
    with pytest.raises(RunPlanningError):
        plan_benchmark_run((), _corpus(tmp_path), "r")


def test_corpus_required(tmp_path: Path) -> None:
    with pytest.raises(RunPlanningError):
        plan_benchmark_run((Competitor(engine="tesseract"),), None, "r")


def test_ocr_only_pipeline_shape(tmp_path: Path) -> None:
    build = plan_benchmark_run(
        (Competitor(engine="tesseract"),), _corpus(tmp_path), "r"
    )
    (pipe,) = build(tmp_path).pipelines
    assert pipe.name == "tesseract"
    (step,) = pipe.steps
    assert step.output_types == (ArtifactType.RAW_TEXT,)


def test_text_and_image_passes_image_to_llm(tmp_path: Path) -> None:
    comp = Competitor(engine="tesseract", mode="text_and_image", llm="openai")
    build = plan_benchmark_run((comp,), _corpus(tmp_path), "r")
    (pipe,) = build(tmp_path).pipelines
    _ocr, llm = pipe.steps
    assert set(llm.input_types) == {ArtifactType.RAW_TEXT, ArtifactType.IMAGE}
    assert llm.inputs_from[ArtifactType.IMAGE] == INITIAL_STEP_ID
    assert llm.inputs_from[ArtifactType.RAW_TEXT] == "ocr"
    assert llm.output_types == (ArtifactType.CORRECTED_TEXT,)


def test_zero_shot_pipeline_shape(tmp_path: Path) -> None:
    comp = Competitor(engine="openai", mode="zero_shot")
    build = plan_benchmark_run((comp,), _corpus(tmp_path), "r")
    (pipe,) = build(tmp_path).pipelines
    (step,) = pipe.steps
    assert step.input_types == (ArtifactType.IMAGE,)
    assert step.output_types == (ArtifactType.RAW_TEXT,)


def test_char_exclude_threaded_to_evaluation_views(tmp_path: Path) -> None:
    # Câblage : le champ ``char_exclude`` du formulaire atterrit sur la vue
    # d'évaluation (le runner l'applique déjà des deux côtés, couche 3).
    build = plan_benchmark_run(
        (Competitor(engine="tesseract"),),
        _corpus(tmp_path),
        "r",
        char_exclude=",.;",
    )
    spec = build(tmp_path)
    assert spec.evaluation.views  # au moins la vue texte
    assert all(v.char_exclude == ",.;" for v in spec.evaluation.views)


def test_char_exclude_absent_by_default(tmp_path: Path) -> None:
    spec = plan_benchmark_run(
        (Competitor(engine="tesseract"),), _corpus(tmp_path), "r"
    )(tmp_path)
    assert all(v.char_exclude is None for v in spec.evaluation.views)


def _text_view_metrics(spec: object) -> tuple[str, ...]:
    views = spec.evaluation.views  # type: ignore[attr-defined]
    text = next(v for v in views if v.name == "text")
    return text.metric_names


def test_air_active_by_default_hcpr_opt_in(tmp_path: Path) -> None:
    # ``air`` est actif d'office (Q4) ; ``hcpr`` n'apparaît PAS sans liste
    # configurée — anti-colonne-jumelle de mufi_err sur corpus médiéval.
    spec = plan_benchmark_run(
        (Competitor(engine="tesseract"),), _corpus(tmp_path), "r"
    )(tmp_path)
    metrics = _text_view_metrics(spec)
    assert "air" in metrics
    assert "hcpr" not in metrics
    # Toujours tracé au manifeste (la liste qu'``air`` a utilisée).
    assert spec.metadata["archaic_list"] == "archaic_core"
    assert len(spec.metadata["archaic_list_hash"]) == 64


def test_numseq_not_in_default_view(tmp_path: Path) -> None:
    # ``numseq_*`` retirés de la vue par défaut (D-130) : adaptatifs → colonnes
    # vides sur corpus sans séquences. La section ``structured_data`` reste,
    # elle, adaptative (collecteur indépendant de ``metric_names``).
    spec = plan_benchmark_run(
        (Competitor(engine="tesseract"),), _corpus(tmp_path), "r"
    )(tmp_path)
    metrics = _text_view_metrics(spec)
    assert "numseq_strict" not in metrics
    assert "numseq_value" not in metrics


def test_configured_archaic_list_enables_hcpr(tmp_path: Path) -> None:
    spec = plan_benchmark_run(
        (Competitor(engine="tesseract"),),
        _corpus(tmp_path),
        "r",
        archaic_list="archaic_core",
    )(tmp_path)
    metrics = _text_view_metrics(spec)
    assert "air" in metrics and "hcpr" in metrics
    assert spec.metadata["archaic_list"] == "archaic_core"


def test_unknown_archaic_list_refused(tmp_path: Path) -> None:
    with pytest.raises(RunPlanningError):
        plan_benchmark_run(
            (Competitor(engine="tesseract"),),
            _corpus(tmp_path),
            "r",
            archaic_list="nope",
        )


def test_ocr_only_model_plumbed_to_engine(tmp_path: Path) -> None:
    # Referme le gap 2c : un moteur OCR à modèle (kraken) reçoit son ``model``
    # depuis le formulaire OCR-seul → il se construit (au lieu d'échouer).
    comp = Competitor(engine="kraken", model="med.mlmodel")
    spec = plan_benchmark_run((comp,), _corpus(tmp_path), "r")(tmp_path)
    kwargs = spec.adapter_kwargs["kraken:c0"]
    assert kwargs["model"] == "med.mlmodel"
    module = _registry().build("kraken:c0", kwargs)
    assert module.name == "kraken:c0"


def test_ocr_only_without_model_omits_it(tmp_path: Path) -> None:
    # Sans modèle saisi, le kwarg n'est pas posé (tesseract n'en veut pas).
    spec = plan_benchmark_run(
        (Competitor(engine="tesseract"),), _corpus(tmp_path), "r"
    )(tmp_path)
    assert "model" not in spec.adapter_kwargs["tesseract:c0"]


def test_curated_prompt_name_resolves_to_text(tmp_path: Path) -> None:
    comp = Competitor(
        engine="openai", mode="zero_shot", prompt_name="zero_shot_medieval_french"
    )
    spec = plan_benchmark_run((comp,), _corpus(tmp_path), "r")(tmp_path)
    resolved = spec.adapter_kwargs["openai:c0"]["prompt"]
    assert isinstance(resolved, str) and len(resolved) > 20  # vrai texte curé
    assert "{ocr_text}" not in resolved  # prompt zero-shot : pas de placeholder


def test_free_prompt_takes_precedence(tmp_path: Path) -> None:
    comp = Competitor(engine="openai", mode="zero_shot", prompt="MON PROMPT")
    spec = plan_benchmark_run((comp,), _corpus(tmp_path), "r")(tmp_path)
    assert spec.adapter_kwargs["openai:c0"]["prompt"] == "MON PROMPT"


def test_prompt_and_prompt_name_together_refused(tmp_path: Path) -> None:
    comp = Competitor(
        engine="openai", mode="zero_shot", prompt="x",
        prompt_name="zero_shot_medieval_french",
    )
    with pytest.raises(RunPlanningError, match="OU"):
        plan_benchmark_run((comp,), _corpus(tmp_path), "r")


def test_unknown_prompt_name_refused(tmp_path: Path) -> None:
    comp = Competitor(engine="openai", mode="zero_shot", prompt_name="bidon")
    with pytest.raises(RunPlanningError, match="inconnu"):
        plan_benchmark_run((comp,), _corpus(tmp_path), "r")


def test_duplicate_competitors_get_unique_names(tmp_path: Path) -> None:
    comps = (Competitor(engine="tesseract"), Competitor(engine="tesseract"))
    build = plan_benchmark_run(comps, _corpus(tmp_path), "r")
    names = [p.name for p in build(tmp_path).pipelines]
    assert len(set(names)) == 2  # noms rendus uniques (pas d'écrasement)


def test_benchmark_runs_n_competitors_in_one_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # tesseract (mocké → "alpha" == GT → CER 0) vs tesseract→openai (LLM mocké →
    # "beta" ≠ GT → CER > 0) : UN run, DEUX pipelines, scorés distinctement.
    monkeypatch.setattr(
        "xerocr.adapters.ocr.tesseract._invoke_tesseract", lambda **_: "alpha"
    )
    monkeypatch.setattr(
        "xerocr.adapters.ocr.tesseract._invoke_tesseract_confidences",
        lambda **_: [],
    )
    monkeypatch.setattr(
        "xerocr.adapters.llm.openai._invoke_openai", lambda **_: LLMCompletion("beta")
    )
    comps = (
        Competitor(engine="tesseract"),
        Competitor(engine="tesseract", mode="text_only", llm="openai"),
    )
    build = plan_benchmark_run(comps, _corpus(tmp_path), "r")
    result = run(build(tmp_path), registry=_registry(), code_version="1.0")
    cer = {
        pr.pipeline: next(s.value for s in pr.aggregate if s.metric == "cer")
        for pr in result.pipelines
    }
    assert cer["tesseract"] == 0.0
    assert (cer["tesseract→openai"] or 0.0) > 0.0


def _status(kind: str, *, available: bool = True) -> EngineStatus:
    return EngineStatus(kind=kind, label=kind.title(), available=available, detail="")


def test_engine_catalog_groups_by_role() -> None:
    statuses = (
        _status("precomputed"),
        _status("tesseract"),
        _status("openai", available=False),
        _status("ollama"),
    )
    catalog = benchmark_engine_catalog(statuses)
    ocr = {e["kind"] for e in catalog["ocr"]}
    llm = {e["kind"] for e in catalog["llm"]}
    vlm = {e["kind"] for e in catalog["vlm"]}
    assert ocr == {"tesseract"}
    assert "openai" in llm and "ollama" in llm  # post-correction texte
    assert "openai" in vlm and "ollama" not in vlm  # ollama : pas de vision
    # precomputed est le moteur de démo, jamais proposé comme concurrent.
    assert "precomputed" not in (ocr | llm | vlm)
    # indisponibilité reflétée (grisé côté UI), pas masquée.
    openai_entry = next(e for e in catalog["llm"] if e["kind"] == "openai")
    assert openai_entry["available"] is False


def test_normalization_profile_set_on_views(tmp_path: Path) -> None:
    build = plan_benchmark_run(
        (Competitor(engine="tesseract"),),
        _corpus(tmp_path),
        "r",
        normalization="medieval_french",
    )
    spec = build(tmp_path)
    assert spec.evaluation.views[0].normalization_profile == "medieval_french"


def test_unknown_normalization_refused(tmp_path: Path) -> None:
    with pytest.raises(RunPlanningError):
        plan_benchmark_run(
            (Competitor(engine="tesseract"),),
            _corpus(tmp_path),
            "r",
            normalization="bogus_profile",
        )


# --- Profil de métriques (sélecteur 3c) --------------------------------------


def _plan_metrics(tmp_path: Path, profile: str | None) -> tuple[str, ...]:
    spec = plan_benchmark_run(
        (Competitor(engine="tesseract"),),
        _corpus(tmp_path),
        "r",
        metric_profile=profile,
    )(tmp_path)
    return _text_view_metrics(spec)


def test_metric_profile_default_is_standard_and_byte_identical(tmp_path: Path) -> None:
    # Sans profil → ``standard`` ; et ``standard`` explicite donne le MÊME tuple
    # (byte-identique à l'historique → aucun golden ne bouge).
    assert _plan_metrics(tmp_path, None) == (
        "cer", "wer", "mer", "searchability", "hallucination", "air",
    )
    assert _plan_metrics(tmp_path, "standard") == _plan_metrics(tmp_path, None)


def test_metric_profile_essentiel_narrows_columns(tmp_path: Path) -> None:
    assert _plan_metrics(tmp_path, "essentiel") == ("cer", "wer", "mer")


def test_metric_profile_philologie_swaps_columns(tmp_path: Path) -> None:
    assert _plan_metrics(tmp_path, "philologie") == (
        "cer", "cer_diplo", "mer", "diacritic_err", "mufi_err", "air",
    )


def test_unknown_metric_profile_refused(tmp_path: Path) -> None:
    with pytest.raises(RunPlanningError, match="profil de métriques inconnu"):
        plan_benchmark_run(
            (Competitor(engine="tesseract"),),
            _corpus(tmp_path),
            "r",
            metric_profile="bidon",
        )


def test_metric_profile_composes_with_hcpr(tmp_path: Path) -> None:
    # Le profil donne la base ; ``hcpr`` (liste archaïque configurée) s'y AJOUTE —
    # les deux axes sont orthogonaux (le profil n'efface pas hcpr).
    spec = plan_benchmark_run(
        (Competitor(engine="tesseract"),),
        _corpus(tmp_path),
        "r",
        metric_profile="essentiel",
        archaic_list="archaic_core",
    )(tmp_path)
    metrics = _text_view_metrics(spec)
    assert metrics == ("cer", "wer", "mer", "hcpr")


def test_metric_profile_catalog_lists_standard_first(tmp_path: Path) -> None:
    catalog = metric_profile_catalog()
    assert catalog[0]["name"] == DEFAULT_METRIC_PROFILE == "standard"
    names = {entry["name"] for entry in catalog}
    assert names == set(METRIC_PROFILES)  # toutes exposées, aucune fantôme
    for entry in catalog:
        assert entry["metrics"] == list(METRIC_PROFILES[entry["name"]])  # ordonné


def test_every_profiled_metric_is_registered(tmp_path: Path) -> None:
    # Garde-fou anti-footgun : une métrique non enregistrée pour (RAW_TEXT,
    # RAW_TEXT) ferait lever le runner (``EvaluationError``) au moment du run.
    # On le verrouille ici, à froid, pour TOUS les profils.
    registry = MetricRegistry()
    register_default_metrics(registry)
    applicable = {
        m.name
        for m in registry.for_input_types(ArtifactType.RAW_TEXT, ArtifactType.RAW_TEXT)
    }
    for name, metrics in METRIC_PROFILES.items():
        unknown = set(metrics) - applicable
        assert not unknown, f"profil {name!r} : métriques non enregistrées {unknown}"
