"""``PPDocLayoutSegmenter`` — segmenteur de mise en page réel (PP-DocLayout).

Détecte les **régions** d'une page (titre, paragraphe, figure, tableau…) et émet
un ``LAYOUT`` (``CanonicalLayout`` à régions **sans lignes** — la reconnaissance
les remplit ensuite, cf. fan-out couche 4). Implémente le ``Module`` Protocol
**directement**, comme les autres adapters.

Module **maison du socle** (≠ plugin tiers découvert) : enregistré par
``register_default_modules`` → disponible **même en mode public** sur le Space
(contrairement aux plugins via entry-points, fail-closed). Son SDK (PaddleX,
Apache-2.0) est un **extra optionnel** (``xerocr[segment]``), importé
**paresseusement** : importer ce module n'exige ni la lib ni les poids — seule
l'exécution les requiert.

Le détecteur est **injectable** (``detector=``) : la conversion détections →
``CanonicalLayout`` se teste sans SDK ni poids (CI), le vrai modèle reste un test
``live``/``slow`` opt-in. Déterminisme (§12) : à modèle + poids + params figés et
seuil de score fixe, la sortie est stable ; l'ordre de lecture est **trié**
(haut→bas puis gauche→droite), indépendant de l'ordre de détection.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from xerocr.adapters._workspace import workspace_artifact_path
from xerocr.domain.artifacts import Artifact, ArtifactType, compute_content_hash
from xerocr.domain.errors import AdapterStepError
from xerocr.domain.layout import BBox, CanonicalLayout, Geometry, LayoutPage, Region
from xerocr.pipeline.protocols import ParamValue
from xerocr.pipeline.run_control import RunControl
from xerocr.pipeline.types import RunContext, StepOutput

_VERSION = "1.0"
_DEFAULT_MIN_SCORE = 0.5


@dataclass(frozen=True)
class DetectedRegion:
    """Une région détectée : étiquette, boîte (pixels) et score de confiance."""

    label: str
    x: int
    y: int
    width: int
    height: int
    score: float


@dataclass(frozen=True)
class LayoutDetection:
    """Sortie brute d'un détecteur : dimensions de page + régions détectées."""

    page_width: int
    page_height: int
    regions: tuple[DetectedRegion, ...]


#: Détecteur **injectable** : chemin image → détection. Le défaut (PaddleX) est
#: résolu paresseusement à l'exécution ; les tests injectent un faux détecteur.
DetectorFn = Callable[[str], LayoutDetection]


def _to_canonical_layout(
    detection: LayoutDetection, *, min_score: float
) -> CanonicalLayout:
    """Détections → ``CanonicalLayout`` (1 page, régions **sans lignes**).

    Filtre au seuil de score, **trie** par position (haut→bas puis gauche→droite)
    pour un ordre de lecture **déterministe** indépendant de l'ordre de détection,
    et numérote les régions ``r1..rN``. Le ``label`` du modèle devient le
    ``region_type`` neutre (``None`` si vide).
    """
    kept = [r for r in detection.regions if r.score >= min_score]
    ordered = sorted(kept, key=lambda r: (r.y, r.x))
    regions = tuple(
        Region(
            id=f"r{index + 1}",
            region_type=r.label or None,
            geometry=Geometry(
                bbox=BBox(x=r.x, y=r.y, width=r.width, height=r.height)
            ),
        )
        for index, r in enumerate(ordered)
    )
    page = LayoutPage(
        width=detection.page_width or None,
        height=detection.page_height or None,
        regions=regions,
        reading_order=tuple(region.id for region in regions),
    )
    return CanonicalLayout(pages=(page,))


def _detect_with_paddle(  # pragma: no cover -- SDK + poids requis (test 'live')
    image_path: str,
) -> LayoutDetection:
    """Détecte la mise en page via **PaddleX PP-DocLayout**. Isolé → mockable.

    SDK absent → ``AdapterStepError`` explicite (l'extra ``[segment]`` manque) ;
    le module reste listable, il ne plante pas à l'import. Le corps qui exécute le
    modèle n'est exercé que par un test ``live`` (SDK + poids installés).
    """
    try:
        from paddlex import create_model  # type: ignore[import-not-found]
    except ImportError as exc:
        raise AdapterStepError(
            "pp_doclayout : PaddleX non installé "
            "(pip install 'xerocr[segment]' + poids PP-DocLayout)."
        ) from exc
    results = list(create_model("PP-DocLayout-L").predict(image_path, batch_size=1))
    if not results:
        return LayoutDetection(page_width=0, page_height=0, regions=())
    boxes = results[0].get("boxes", [])
    regions = tuple(
        DetectedRegion(
            label=str(box.get("label", "")),
            x=int(box["coordinate"][0]),
            y=int(box["coordinate"][1]),
            width=int(box["coordinate"][2]) - int(box["coordinate"][0]),
            height=int(box["coordinate"][3]) - int(box["coordinate"][1]),
            score=float(box.get("score", 0.0)),
        )
        for box in boxes
    )
    shape = results[0].get("input_img_shape") or (0, 0)
    return LayoutDetection(
        page_width=int(shape[1]), page_height=int(shape[0]), regions=regions
    )


class PPDocLayoutSegmenter:
    """Segmenteur PP-DocLayout : ``IMAGE → LAYOUT`` (régions sans lignes)."""

    def __init__(
        self,
        *,
        min_score: float = _DEFAULT_MIN_SCORE,
        detector: DetectorFn | None = None,
    ) -> None:
        if not 0.0 <= min_score <= 1.0:
            raise AdapterStepError(
                f"PPDocLayoutSegmenter : min_score ∈ [0, 1], reçu {min_score}."
            )
        self._min_score = min_score
        self._detector = detector

    @property
    def name(self) -> str:
        return "pp_doclayout"

    @property
    def version(self) -> str:
        return _VERSION

    @property
    def input_types(self) -> frozenset[ArtifactType]:
        return frozenset({ArtifactType.IMAGE})

    @property
    def output_types(self) -> frozenset[ArtifactType]:
        return frozenset({ArtifactType.LAYOUT})

    def _detect(self, image_path: str) -> LayoutDetection:
        if self._detector is not None:
            return self._detector(image_path)
        return _detect_with_paddle(image_path)

    def execute(
        self,
        inputs: dict[ArtifactType, Artifact],
        params: dict[str, ParamValue],
        context: RunContext,
        control: RunControl,
    ) -> StepOutput:
        control.raise_if_cancelled()
        image = inputs.get(ArtifactType.IMAGE)
        if image is None or image.uri is None:
            raise AdapterStepError(
                f"{self.name} : artefact IMAGE manquant ou sans URI."
            )
        if context.workspace_uri is None:
            raise AdapterStepError(
                f"{self.name} : workspace requis (RunContext.workspace_uri)."
            )
        layout = _to_canonical_layout(
            self._detect(image.uri), min_score=self._min_score
        )
        payload = layout.model_dump_json().encode("utf-8")
        output_path = workspace_artifact_path(
            context.workspace_uri, context.document_id, self.name, "layout.json"
        )
        output_path.write_bytes(payload)
        return StepOutput(
            artifacts={
                ArtifactType.LAYOUT: Artifact(
                    id=f"{context.document_id}:{self.name}:layout",
                    document_id=context.document_id,
                    type=ArtifactType.LAYOUT,
                    uri=str(output_path),
                    content_hash=compute_content_hash(payload),
                )
            }
        )


__all__ = ["DetectedRegion", "LayoutDetection", "PPDocLayoutSegmenter"]
