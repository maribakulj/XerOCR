"""Fan-out par région — le cœur net-new de la tranche segmentation (couche 4).

``segmentation (IMAGE → LAYOUT régions-seules) → reconnaissance PAR RÉGION (remplit
le LAYOUT)``. Le ``Module`` reste **inchangé** : il renvoie *un* artefact par type ;
c'est **l'orchestration** (ici) qui boucle sur les N régions, collecte les N
sorties (estampillées ``region_id``), **tolère les échecs partiels** (une région
qui échoue n'abat pas la page) et réassemble en respectant l'ordre de lecture.

Le recognizer reçoit une IMAGE **cadrée par région** (``region_id`` posé) ; en
socle ``precomputed`` aucun découpage réel n'a lieu (la donnée est figée par
région). Le découpage pixel réel est un épaississement (concern adapter).
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path

from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.domain.errors import AdapterStepError
from xerocr.domain.layout import CanonicalLayout, LayoutPage, Line, Region
from xerocr.pipeline.protocols import Module, ParamValue
from xerocr.pipeline.run_control import RunControl
from xerocr.pipeline.types import RunContext

logger = logging.getLogger(__name__)


def run_region_fanout(
    *,
    layout: CanonicalLayout,
    page_image: Artifact,
    recognizer: Module,
    context: RunContext,
    control: RunControl,
    params: Mapping[str, ParamValue] | None = None,
) -> CanonicalLayout:
    """Remplit ``layout`` (régions seules) par reconnaissance région par région.

    Renvoie un nouveau ``CanonicalLayout`` où chaque région porte sa ligne de
    texte reconnu. Une région dont la reconnaissance échoue reste **vide** (texte
    non produit, avertissement journalisé) — la page n'est pas abattue.
    """
    step_params = dict(params) if params is not None else {}
    pages = tuple(
        _fill_page(page, page_image, recognizer, context, control, step_params)
        for page in layout.pages
    )
    return CanonicalLayout(pages=pages)


def _fill_page(
    page: LayoutPage,
    page_image: Artifact,
    recognizer: Module,
    context: RunContext,
    control: RunControl,
    params: dict[str, ParamValue],
) -> LayoutPage:
    filled = tuple(
        _fill_region(region, page_image, recognizer, context, control, params)
        for region in page.regions
    )
    return page.model_copy(update={"regions": filled})


def _fill_region(
    region: Region,
    page_image: Artifact,
    recognizer: Module,
    context: RunContext,
    control: RunControl,
    params: dict[str, ParamValue],
) -> Region:
    control.raise_if_cancelled()
    region_image = page_image.model_copy(
        update={
            "id": f"{page_image.id}:{region.id}",
            "region_id": region.id,
            "produced_by_step": None,
            "provenance": None,
        }
    )
    try:
        outputs = recognizer.execute(
            {ArtifactType.IMAGE: region_image}, dict(params), context, control
        )
        text = _read_text(outputs)
    except AdapterStepError as exc:
        logger.warning(
            "[fanout] région %r non reconnue (ignorée) : %s", region.id, exc
        )
        return region
    line = Line(id=f"{region.id}:l1", text=text)
    return region.model_copy(update={"lines": (line,)})


def _read_text(outputs: dict[ArtifactType, Artifact]) -> str:
    artifact = outputs.get(ArtifactType.RAW_TEXT)
    if artifact is None or artifact.uri is None:
        raise AdapterStepError("fanout : reconnaissance sans RAW_TEXT exploitable.")
    try:
        return Path(artifact.uri).read_text(encoding="utf-8")
    except OSError as exc:
        raise AdapterStepError(f"fanout : texte de région illisible : {exc}") from exc


__all__ = ["run_region_fanout"]
