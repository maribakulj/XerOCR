"""Qualité d'image mesurée **par document** (couche 3, scope corpus).

Mesure des features réelles de la numérisation — netteté, bruit, contraste,
inclinaison résiduelle — combinées en un score [0,1]. Sert à **expliquer** un
CER élevé (image dégradée vs moteur faible), jamais à le prédire : la
re-pondération « prédictive » de la source (``image_predictive`` — aucun pouvoir
prédictif réel, simple combinaison des mêmes features sous un nom mensonger) est
**abandonnée** (D-128).

⚠️ **Constantes = conventions éditoriales (R8).** Aucune n'a d'autorité
scientifique externe : ce sont des **choix de produit** sur ce qui rend une
numérisation « bonne », chacun documenté avec sa lecture et révisable. On ne les
présente jamais comme des seuils physiques.

NumPy fait les maths (garanti — ``scipy`` le tire en dépendance cœur). Pillow ne
fait que **décoder** l'image (extra ``[images]``) ; absent → la mesure est non
applicable (``None`` + warning unique), jamais un score fabriqué (R9 : le
``generate_mock_quality_scores`` de la source — canal environnemental — n'est pas
porté ; la démo XerOCR reste octet-stable).
"""

from __future__ import annotations

import io
import logging
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean

import numpy as np
from numpy.typing import NDArray

from xerocr.domain.corpus import CorpusSpec
from xerocr.evaluation.analysis import (
    Analysis,
    DocumentImageQuality,
    ImageQualityPayload,
)

logger = logging.getLogger(__name__)

Array = NDArray[np.float64]

#: Échelle de la netteté : variance du laplacien 3×3 ≥ 500 → « net » (score 1,0),
#: ~0 → flou. **Convention éditoriale** (pas un seuil optique) — ordre de grandeur
#: observé sur des numérisations patrimoniales ; révisable sans casser le contrat.
_SHARPNESS_SCALE = 500.0

#: Échelle du bruit : médiane des |gradients| (sur 0–255) ≥ 30 → « bruité »
#: (score 1,0). **Convention éditoriale.**
_NOISE_SCALE = 30.0

#: Poids de la qualité composite (somme = 1,0) : la netteté prime, l'inclinaison
#: pèse le moins (corrigeable au redressement, n'altère pas le texte).
#: **Convention éditoriale assumée** — une opinion de produit, pas une dérivation.
_W_SHARPNESS = 0.40
_W_CONTRAST = 0.30
_W_NOISE = 0.20
_W_ROTATION = 0.10

#: Inclinaison : la contribution rotation décroît linéairement de 1 (0°) à 0
#: (≥ 10°). **Convention éditoriale.**
_ROTATION_FULL_PENALTY_DEG = 10.0

#: Paliers d'affichage (``≥`` seuil). **Conventions éditoriales.**
_GOOD_THRESHOLD = 0.70
_MEDIUM_THRESHOLD = 0.40

#: Balayage d'inclinaison : ±5°, pas de 1° — heuristique de projection bornée
#: (au-delà, on ne prétend pas mesurer). **Convention éditoriale.**
_ROTATION_MAX_DEG = 5

#: Percentiles fond/encre du contraste Michelson (robustes aux pixels extrêmes :
#: poussière, perforations). **Convention éditoriale.**
_CONTRAST_DARK_PCT = 5.0
_CONTRAST_LIGHT_PCT = 95.0

#: Côté minimal (px) pour estimer l'inclinaison — sous lui, la projection n'a pas
#: de signal fiable → 0,0 (pas de fausse précision).
_MIN_ROTATION_SIZE = 20


@dataclass(frozen=True)
class ImageMeasurement:
    """Mesures d'une image (arrondies), avant emballage dans le payload."""

    sharpness: float
    noise: float
    contrast: float
    rotation_degrees: float
    quality_score: float
    tier: str


def laplacian_sharpness(array: Array) -> float:
    """Netteté ∈ [0,1] = variance du laplacien 3×3 / 500, plafonnée à 1.

    Le laplacien (somme des 4 voisins − 4·centre) répond aux transitions nettes ;
    sa **variance** mesure la quantité de détail haute-fréquence — un flou
    l'écrase. Bords ignorés (intérieur seul). Image < 3 px → variance globale.
    """
    height, width = array.shape
    if height < 3 or width < 3:
        variance = float(np.var(array))
    else:
        center = array[1:-1, 1:-1]
        laplacian = (
            array[:-2, 1:-1]
            + array[2:, 1:-1]
            + array[1:-1, :-2]
            + array[1:-1, 2:]
            - 4.0 * center
        )
        variance = float(np.var(laplacian))
    return min(1.0, variance / _SHARPNESS_SCALE)


def gradient_noise(array: Array) -> float:
    """Bruit ∈ [0,1] = médiane des |gradients| / 30, plafonnée à 1.

    Médiane de la valeur absolue des différences de pixels voisins (horizontales
    ∪ verticales) — un proxy du bruit haute-fréquence. (La source la nomme « MAD »
    par abus : c'est la **médiane de |∇|**, pas l'écart médian absolu à la
    médiane.) Image < 2 px → 0.
    """
    height, width = array.shape
    if height < 2 or width < 2:
        return 0.0
    horizontal = np.abs(array[:, 1:] - array[:, :-1])
    vertical = np.abs(array[1:, :] - array[:-1, :])
    gradients = np.concatenate([horizontal.ravel(), vertical.ravel()])
    return min(1.0, float(np.median(gradients)) / _NOISE_SCALE)


def michelson_contrast(array: Array) -> float:
    """Contraste Michelson ∈ [0,1] = (p95 − p5) / (p95 + p5) sur les gris.

    Percentiles 5 (fond/encre sombre) et 95 (clair) plutôt que min/max : robuste
    aux pixels extrêmes. 0 si l'image est uniforme (p5 + p95 = 0, ou égaux).
    """
    dark = float(np.percentile(array, _CONTRAST_DARK_PCT))
    light = float(np.percentile(array, _CONTRAST_LIGHT_PCT))
    total = light + dark
    if total <= 0:
        return 0.0
    return min(1.0, max(0.0, (light - dark) / total))


def estimate_rotation(array: Array) -> float:
    """Inclinaison résiduelle estimée (°, signée, dans [−5, +5]) — heuristique.

    Pour chaque angle de −5° à +5° (pas 1°), on décale chaque ligne de
    ``i·tan(angle)`` et on mesure la **variance des sommes de lignes** : l'angle
    qui la maximise aligne le mieux les lignes de texte (lignes alignées →
    projection horizontale contrastée). **Heuristique grossière** (pas une
    transformée de Hough), volontairement bornée ±5° — au-delà, on ne prétend pas
    mesurer. Image < 20 px → 0,0 (signal non fiable). Déterministe : à variance
    égale, le **premier** angle balayé (le plus petit) gagne (``>`` strict).
    """
    height, width = array.shape
    if height < _MIN_ROTATION_SIZE or width < _MIN_ROTATION_SIZE:
        return 0.0
    step = max(1, height // 100)  # sous-échantillonnage : coût borné
    sample = array[::step, :]
    rows = int(sample.shape[0])
    indices = np.arange(rows)
    best_angle = 0.0
    best_variance = -1.0
    for angle in range(-_ROTATION_MAX_DEG, _ROTATION_MAX_DEG + 1):
        offsets = np.round(indices * math.tan(math.radians(angle))).astype(int)
        offsets = np.clip(offsets, 0, width - 1)
        row_sums = np.array(
            [float(np.sum(sample[i, int(offsets[i]) :])) for i in range(rows)]
        )
        variance = float(np.var(row_sums))
        if variance > best_variance:
            best_variance = variance
            best_angle = float(angle)
    return best_angle


def composite_quality(
    sharpness: float, noise: float, rotation_abs: float, contrast: float
) -> float:
    """Score qualité ∈ [0,1] : 0.40·netteté + 0.30·contraste + 0.20·(1−bruit)
    + 0.10·max(0, 1−|rotation|/10). **Convention éditoriale (R8).**"""
    score = (
        _W_SHARPNESS * sharpness
        + _W_CONTRAST * contrast
        + _W_NOISE * (1.0 - noise)
        + _W_ROTATION * max(0.0, 1.0 - rotation_abs / _ROTATION_FULL_PENALTY_DEG)
    )
    return min(1.0, max(0.0, score))


def quality_tier(score: float) -> str:
    """Palier (``≥`` seuil) : good ≥ 0.70 · medium ≥ 0.40 · poor sinon (R8)."""
    if score >= _GOOD_THRESHOLD:
        return "good"
    if score >= _MEDIUM_THRESHOLD:
        return "medium"
    return "poor"


def measure_grayscale(array: Array) -> ImageMeasurement:
    """Mesure complète d'une image niveaux de gris (matrice 2D) — arrondie.

    Arrondis (4 décimales, 2 pour l'angle) = byte-stabilité du rapport/JSON malgré
    le bruit flottant inter-plateformes.
    """
    sharpness = laplacian_sharpness(array)
    noise = gradient_noise(array)
    contrast = michelson_contrast(array)
    rotation = estimate_rotation(array)
    quality = round(composite_quality(sharpness, noise, abs(rotation), contrast), 4)
    return ImageMeasurement(
        sharpness=round(sharpness, 4),
        noise=round(noise, 4),
        contrast=round(contrast, 4),
        rotation_degrees=round(rotation, 2),
        quality_score=quality,
        tier=quality_tier(quality),
    )


def image_quality_analysis(view: str, corpus: CorpusSpec) -> Analysis | None:
    """Qualité des images du corpus (scope corpus) ; ``None`` si non applicable.

    Mesurée **une seule fois par document** (indépendante du pipeline et de la
    vue). ``None`` si Pillow est absent (warning unique) ou si aucun document n'a
    d'image **locale lisible** (adaptatif). Les images distantes (``://``),
    manquantes ou non décodables sont **exclues** avec un warning — jamais une
    mesure fabriquée (≠ le mock de la source).
    """
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError as exc:
        logger.warning(
            "[image_quality] Pillow absent (extra [images]) — qualité d'image "
            "non mesurée : %s",
            exc,
        )
        return None

    rows: list[DocumentImageQuality] = []
    for document in corpus.documents:
        uri = document.image_uri
        if uri is None or "://" in uri:
            continue  # purement textuel, ou référence distante (non lisible ici)
        try:
            data = Path(uri).read_bytes()
        except OSError as exc:
            logger.warning("[image_quality] image illisible (%s) : %s", uri, exc)
            continue
        try:
            with Image.open(io.BytesIO(data)) as image:
                array = np.asarray(image.convert("L"), dtype=np.float64)
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            logger.warning(
                "[image_quality] image non décodable (%s) : %s", uri, exc
            )
            continue
        if array.size == 0:
            logger.warning("[image_quality] image vide (0 pixel) : %s", uri)
            continue
        measurement = measure_grayscale(array)
        rows.append(
            DocumentImageQuality(
                document_id=document.id,
                sharpness=measurement.sharpness,
                noise=measurement.noise,
                contrast=measurement.contrast,
                rotation_degrees=measurement.rotation_degrees,
                quality_score=measurement.quality_score,
                tier=measurement.tier,
            )
        )

    if not rows:
        return None
    payload = ImageQualityPayload(
        documents=tuple(rows),
        mean_quality=round(fmean(row.quality_score for row in rows), 4),
        mean_sharpness=round(fmean(row.sharpness for row in rows), 4),
        mean_noise=round(fmean(row.noise for row in rows), 4),
        mean_contrast=round(fmean(row.contrast for row in rows), 4),
        n_good=sum(1 for row in rows if row.tier == "good"),
        n_medium=sum(1 for row in rows if row.tier == "medium"),
        n_poor=sum(1 for row in rows if row.tier == "poor"),
    )
    return Analysis(scope="corpus", view=view, payload=payload)


__all__ = [
    "ImageMeasurement",
    "composite_quality",
    "estimate_rotation",
    "gradient_noise",
    "image_quality_analysis",
    "laplacian_sharpness",
    "measure_grayscale",
    "michelson_contrast",
    "quality_tier",
]
