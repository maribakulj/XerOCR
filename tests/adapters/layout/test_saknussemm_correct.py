"""``SaknussemmCorrector`` : corriger **dans** la mise en page.

La post-correction du banc était texte plat → texte plat : on aplatissait avant
de corriger, donc l'identité de ligne mourait avant que le modèle voie quoi que
ce soit. Ici elle survit, et l'appariement avant/après est **connu** au lieu
d'être deviné par un alignement de Levenshtein sur des listes de lignes.

Les tests utilisent le producteur ``rules`` : déterministe, hors ligne, aucune
dépendance réseau. Ce qui est vérifié est le **chemin**, pas la qualité d'un
modèle.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cinoc.adapters.layout.saknussemm_correct import SaknussemmCorrector, _flatten
from cinoc.adapters.layout.to_text import LayoutToTextExtractor
from cinoc.domain.artifacts import Artifact, ArtifactType
from cinoc.domain.errors import AdapterStepError
from cinoc.domain.layout import (
    BBox,
    CanonicalLayout,
    Geometry,
    LayoutPage,
    Line,
    Region,
)
from cinoc.pipeline.run_control import RunControl
from cinoc.pipeline.types import RunContext

saknussemm = pytest.importorskip("saknussemm")


def _layout(*texts: str) -> CanonicalLayout:
    return CanonicalLayout(
        pages=(
            LayoutPage(
                width=600,
                height=400,
                regions=(
                    Region(
                        id="R1",
                        geometry=Geometry(bbox=BBox(x=0, y=0, width=600, height=400)),
                        lines=tuple(
                            Line(
                                id=f"L{i + 1}",
                                text=text,
                                geometry=Geometry(
                                    bbox=BBox(x=10, y=20 * i, width=500, height=18)
                                ),
                            )
                            for i, text in enumerate(texts)
                        ),
                    ),
                ),
            ),
        )
    )


def _run(tmp_path: Path, layout: CanonicalLayout) -> dict[ArtifactType, Artifact]:
    src = tmp_path / "in.layout.json"
    src.write_bytes(layout.model_dump_json().encode("utf-8"))
    out = SaknussemmCorrector(label="regles").execute(
        {
            ArtifactType.LAYOUT: Artifact(
                id="a",
                document_id="doc1",
                type=ArtifactType.LAYOUT,
                uri=str(src),
                content_hash="0" * 64,
            )
        },
        {},
        RunContext(
            document_id="doc1",
            code_version="1.0",
            pipeline_name="p",
            workspace_uri=str(tmp_path / "ws"),
        ),
        RunControl(),
    )
    return out.artifacts


def _lines(artifact: Artifact) -> list[Line]:
    layout = CanonicalLayout.model_validate_json(Path(artifact.uri).read_bytes())
    return [ln for p in layout.pages for r in p.regions for ln in r.lines]


def test_a_correction_actually_happens(tmp_path: Path) -> None:
    """**Contrôle de sensibilité, et il vient en premier.**

    Sans lui, « 0 ligne modifiée » ne distingue pas « rien à corriger » de
    « le module ne corrige rien ». Le ``ſ`` long est l'une des trois
    substitutions des règles françaises par défaut.
    """
    arts = _run(tmp_path, _layout("le ſoleil ſe lève"))
    assert _lines(arts[ArtifactType.LAYOUT])[0].text == "le soleil se lève"


def test_line_identity_survives_the_corrector(tmp_path: Path) -> None:
    """C'est la raison d'être de l'étape : l'appariement avant/après est connu."""
    arts = _run(tmp_path, _layout("le ſoleil", "brille", "ſur la mer"))
    assert [ln.id for ln in _lines(arts[ArtifactType.LAYOUT])] == ["L1", "L2", "L3"]


def test_geometry_is_kept_but_words_are_dropped_when_the_text_changed(
    tmp_path: Path,
) -> None:
    """Une ligne modifiée garde sa boîte et perd ses mots.

    La géométrie de la ligne décrit toujours la même bande d'image ; celle des
    mots décrivait des caractères qui ne sont plus là. Les garder ferait dire à
    l'artefact une position que rien ne soutient.
    """
    arts = _run(tmp_path, _layout("le ſoleil"))
    line = _lines(arts[ArtifactType.LAYOUT])[0]
    assert line.geometry is not None and line.geometry.bbox is not None
    assert line.words == ()


def test_an_untouched_line_is_returned_verbatim(tmp_path: Path) -> None:
    """Ce que la bibliothèque n'a pas décidé de changer ressort intact."""
    arts = _run(tmp_path, _layout("rien à corriger ici"))
    assert _lines(arts[ArtifactType.LAYOUT])[0].text == "rien à corriger ici"


def test_the_three_outputs_are_produced(tmp_path: Path) -> None:
    """``CORRECTED_TEXT`` fait fonctionner le bilan de correction existant
    **sans le modifier** ; ``DECISIONS`` porte ce qu'un texte corrigé ne peut
    pas dire — ce qui a été refusé, et pourquoi."""
    arts = _run(tmp_path, _layout("le ſoleil"))
    assert set(arts) == {
        ArtifactType.LAYOUT,
        ArtifactType.CORRECTED_TEXT,
        ArtifactType.DECISIONS,
    }
    text = Path(arts[ArtifactType.CORRECTED_TEXT].uri).read_text(encoding="utf-8")
    assert text == "le soleil"


def test_the_decisions_say_what_happened_to_each_line(tmp_path: Path) -> None:
    """Une ligne intacte et une ligne corrigée sont **distinguables** ici.

    Dans le texte corrigé seul, elles ne le sont pas : c'est toute la raison
    d'être de cet artefact.
    """
    import json

    arts = _run(tmp_path, _layout("le ſoleil", "rien à corriger"))
    decisions = json.loads(
        Path(arts[ArtifactType.DECISIONS].uri).read_text(encoding="utf-8")
    )
    par_id = {ligne["line_id"]: ligne for ligne in decisions["lines"]}
    assert par_id["L1"]["source_text"] == "le ſoleil"
    assert par_id["L1"]["final_text"] == "le soleil"
    assert par_id["L2"]["source_text"] == par_id["L2"]["final_text"]
    assert {"status", "reason_code", "proposed_text"} <= set(par_id["L1"])


def test_flattening_matches_to_text_exactly(tmp_path: Path) -> None:
    """Deux conventions d'aplatissement différentes fausseraient la comparaison
    avant/après **sans rien casser de visible**.

    Une première version réécrivait la boucle et ajoutait une ligne vide par
    région sans texte — 41 de trop sur le corpus BnF, soit tout l'appariement
    décalé. La fonction de ``to_text`` est donc réutilisée, pas recopiée.
    """
    layout = CanonicalLayout(
        pages=(
            LayoutPage(
                regions=(
                    Region(id="R1", lines=(Line(id="L1", text="du texte"),)),
                    Region(id="R2", lines=()),  # une illustration, par exemple
                    Region(id="R3", lines=(Line(id="L2", text="encore"),)),
                ),
            ),
        )
    )
    src = tmp_path / "l.json"
    src.write_bytes(layout.model_dump_json().encode("utf-8"))
    ref = LayoutToTextExtractor(label="x").execute(
        {
            ArtifactType.LAYOUT: Artifact(
                id="a",
                document_id="d",
                type=ArtifactType.LAYOUT,
                uri=str(src),
                content_hash="0" * 64,
            )
        },
        {},
        RunContext(
            document_id="d",
            code_version="1",
            pipeline_name="p",
            workspace_uri=str(tmp_path),
        ),
        RunControl(),
    )
    attendu = Path(ref.artifacts[ArtifactType.RAW_TEXT].uri).read_text(encoding="utf-8")
    assert _flatten(layout) == attendu


def test_a_line_without_id_is_refused(tmp_path: Path) -> None:
    """``(page, ligne)`` est une identité, pas un rang — la cause est nommée ici."""
    layout = CanonicalLayout(
        pages=(LayoutPage(regions=(Region(id="R1", lines=(Line(text="anonyme"),)),)),)
    )
    with pytest.raises(AdapterStepError, match="identité"):
        _run(tmp_path, layout)


def test_an_unknown_producer_is_refused_at_construction() -> None:
    with pytest.raises(AdapterStepError, match="producteur"):
        SaknussemmCorrector(label="x", producer="devine")


def test_ollama_without_a_model_is_refused_at_construction() -> None:
    """Un producteur réseau sans modèle échouerait au premier appel, loin d'ici."""
    with pytest.raises(AdapterStepError, match="model"):
        SaknussemmCorrector(label="x", producer="ollama")


def test_registered_under_its_own_kind() -> None:
    from cinoc.app.modules.registry import ModuleRegistry, register_default_modules

    registry = ModuleRegistry()
    register_default_modules(registry)
    module = registry.build("saknussemm:regles", {"label": "regles"})
    assert module.input_types == frozenset({ArtifactType.LAYOUT})
    assert module.output_types == frozenset(
        {
            ArtifactType.LAYOUT,
            ArtifactType.CORRECTED_TEXT,
            ArtifactType.DECISIONS,
        }
    )
