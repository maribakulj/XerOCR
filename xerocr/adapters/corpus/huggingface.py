"""Découverte de datasets HTR/OCR sur **HuggingFace Hub** — couche 5.

Recherche (découverte), pas matérialisation : on liste des datasets candidats
(socle de **référence** intégré + API publique du Hub). Le téléchargement effectif
d'un dataset (lib ``datasets``, dépendance lourde) est un extra **ultérieur**
(`xerocr[huggingface]`), hors de cette tranche.

L'appel API est **best-effort** : s'il échoue, on renvoie le socle de référence
(``source="reference"``) en journalisant — l'utilisateur n'est jamais bloqué, et
sait d'où vient chaque résultat (``source`` : ``reference`` | ``api``).
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import urlencode

from xerocr.adapters.corpus._http import (
    DEFAULT_TIMEOUT,
    IMAGE_MAX_BYTES,
    HttpFetchError,
    fetch_json,
)
from xerocr.domain.errors import XerOCRError

logger = logging.getLogger(__name__)

HF_API_BASE = "https://huggingface.co/api"

#: Convention XerOCR (cf. ``docs/corpus_huggingface.md``) : un dataset importable
#: porte **au minimum** une colonne image et une colonne vérité-terrain. La
#: segmentation est une extension *future* (non requise ici).
XEROCR_IMAGE_COLUMN = "image"
XEROCR_GT_COLUMN = "ground_truth"

#: Extensions image reconnues (sinon ``.jpg`` par défaut) pour nommer le fichier.
_IMAGE_EXTS = frozenset({".png", ".jpg", ".jpeg", ".tif", ".tiff", ".jp2", ".webp"})


@dataclass(frozen=True)
class HuggingFaceDataset:
    """Un dataset candidat (métadonnées de découverte)."""

    dataset_id: str
    title: str
    description: str
    languages: tuple[str, ...]
    downloads: int
    source: str  # "reference" | "api"

    @property
    def hf_url(self) -> str:
        return f"https://huggingface.co/datasets/{self.dataset_id}"


def _ref(
    dataset_id: str, title: str, desc: str, langs: tuple[str, ...], dl: int
) -> HuggingFaceDataset:
    return HuggingFaceDataset(
        dataset_id=dataset_id,
        title=title,
        description=desc,
        languages=langs,
        downloads=dl,
        source="reference",
    )


#: Socle de référence minimal (datasets HTR/OCR patrimoniaux connus).
_REFERENCE_DATASETS: tuple[HuggingFaceDataset, ...] = (
    _ref(
        "Teklia/NorHand", "NorHand", "Écriture manuscrite norvégienne.", ("no",), 1200
    ),
    _ref(
        "Teklia/IAM-line",
        "IAM (lignes)",
        "Référence anglaise manuscrite.",
        ("en",),
        8400,
    ),
    _ref(
        "bnf/gallica-presse-xix",
        "Gallica Presse XIXe",
        "Journaux numérisés XIXe (OCR + images).",
        ("fr",),
        15200,
    ),
)


def _matches(ds: HuggingFaceDataset, query: str, language: str | None) -> bool:
    if query:
        q = query.lower()
        if not (
            q in ds.title.lower()
            or q in ds.description.lower()
            or q in ds.dataset_id.lower()
            or any(q in lg.lower() for lg in ds.languages)
        ):
            return False
    if language and not any(language.lower() in lg.lower() for lg in ds.languages):
        return False
    return True


def search_reference(
    query: str = "", language: str | None = None
) -> tuple[HuggingFaceDataset, ...]:
    """Filtre le socle de référence intégré. Pur (sans réseau)."""
    return tuple(ds for ds in _REFERENCE_DATASETS if _matches(ds, query, language))


def _parse_api(payload: object) -> tuple[HuggingFaceDataset, ...]:
    """Mappe la réponse de l'API HF (liste de dicts) → datasets. Pur."""
    if not isinstance(payload, list):
        return ()
    out: list[HuggingFaceDataset] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        dataset_id = str(item.get("id", "") or "")
        if not dataset_id:
            continue
        downloads = item.get("downloads", 0)
        out.append(
            HuggingFaceDataset(
                dataset_id=dataset_id,
                title=dataset_id,
                description="",
                languages=(),
                downloads=int(downloads) if isinstance(downloads, int) else 0,
                source="api",
            )
        )
    return tuple(out)


class HuggingFaceCatalogue:
    """Recherche de datasets : socle de référence + API publique (best-effort)."""

    name = "huggingface"

    def __init__(
        self, *, api_base: str = HF_API_BASE, timeout: float = DEFAULT_TIMEOUT
    ) -> None:
        self._api_base = api_base.rstrip("/")
        self._timeout = timeout

    def _fetch_api(
        self, query: str, language: str | None, limit: int
    ) -> tuple[HuggingFaceDataset, ...]:
        params: dict[str, str] = {
            "task_categories": "image-to-text",
            "limit": str(min(limit, 50)),
        }
        if query:
            params["search"] = query
        if language:
            params["language"] = language
        url = f"{self._api_base}/datasets?{urlencode(params)}"
        return _parse_api(fetch_json(url, timeout=self._timeout))

    def search(
        self,
        query: str = "",
        language: str | None = None,
        *,
        limit: int = 20,
        use_reference: bool = True,
        include_api: bool = True,
    ) -> tuple[HuggingFaceDataset, ...]:
        results: list[HuggingFaceDataset] = []
        if use_reference:
            results.extend(search_reference(query, language))
        if include_api:
            seen = {ds.dataset_id for ds in results}
            try:
                for ds in self._fetch_api(query, language, limit):
                    if ds.dataset_id not in seen:
                        results.append(ds)
                        seen.add(ds.dataset_id)
            except HttpFetchError as exc:
                logger.warning(
                    "[huggingface] recherche API indisponible — socle de référence "
                    "seul : %s",
                    exc,
                )
        # Accept #9 : socle de référence d'abord, API ensuite, puis troncature
        # finale à `limit` — la référence (curée) prime sur l'API si l'union
        # dépasse. Choix de découverte (display), pas de classement par score.
        return tuple(results[:limit])


class HuggingFaceConventionError(XerOCRError):
    """Le dataset ne respecte pas la **convention XerOCR** (colonnes attendues)."""


class HuggingFaceUnavailableError(XerOCRError):
    """La lib ``datasets`` (extra ``[huggingface]``) n'est pas installée."""


@dataclass(frozen=True)
class HFPage:
    """Une page **streamée** : octets image encodés + extension + texte GT.

    Type neutre à la frontière adapter→app : l'image est livrée en **octets**
    (jamais un objet PIL) pour que la matérialisation disque (couche 6) n'ait
    aucune dépendance image.
    """

    image_bytes: bytes
    image_ext: str
    gt_text: str


#: Charge un dataset en streaming → itérable de lignes. Injectable (test).
HFLoader = Callable[[str, str], Iterable[object]]


def _default_loader(dataset_id: str, split: str) -> Iterable[object]:
    """Charge le dataset HF **en streaming** (jamais de snapshot local complet).

    Import **paresseux** de ``datasets`` (extra ``[huggingface]``) : sans l'extra,
    lève ``HuggingFaceUnavailableError`` (message actionnable). Les images sont
    castées en ``Image(decode=False)`` → octets bruts (pas de décodage PIL).
    """
    try:
        from datasets import Image, load_dataset  # type: ignore[import-not-found]
    except ImportError as exc:
        raise HuggingFaceUnavailableError(
            "import HuggingFace indisponible : installer 'xerocr[huggingface]' "
            "(lib 'datasets')."
        ) from exc
    dataset = load_dataset(dataset_id, split=split, streaming=True)
    features = getattr(dataset, "features", None) or {}
    if XEROCR_IMAGE_COLUMN in features:
        dataset = dataset.cast_column(XEROCR_IMAGE_COLUMN, Image(decode=False))
    return dataset  # type: ignore[no-any-return]


def _ext_from_path(path: object) -> str:
    if isinstance(path, str) and path:
        suffix = PurePosixPath(path).suffix.lower()
        if suffix in _IMAGE_EXTS:
            return suffix
    return ".jpg"


def _extract_image(value: object) -> tuple[bytes, str]:
    """Octets image + extension depuis une cellule ``image`` (``decode=False``)."""
    if isinstance(value, dict):
        raw = value.get("bytes")
        if isinstance(raw, bytes) and raw:
            return raw, _ext_from_path(value.get("path"))
    raise HuggingFaceConventionError(
        f"colonne {XEROCR_IMAGE_COLUMN!r} : octets image absents (le dataset "
        "doit stocker l'image en octets ; cf. convention XerOCR)."
    )


def _validate_columns(row: dict[str, object]) -> None:
    missing = [c for c in (XEROCR_IMAGE_COLUMN, XEROCR_GT_COLUMN) if c not in row]
    if missing:
        raise HuggingFaceConventionError(
            f"dataset non conforme à la convention XerOCR : colonnes manquantes "
            f"{missing} (attendu : {XEROCR_IMAGE_COLUMN!r} + {XEROCR_GT_COLUMN!r})."
        )


def stream_pages(
    dataset_id: str,
    *,
    split: str = "train",
    limit: int | None = None,
    loader: HFLoader | None = None,
) -> Iterator[HFPage]:
    """Streame les pages d'un dataset HF conforme à la **convention XerOCR**.

    Page-par-page (``streaming=True`` côté ``datasets``) : on ne télécharge jamais
    le snapshot complet ; ``limit`` borne le nombre de pages lues. La conformité
    (colonnes ``image`` + ``ground_truth``) est validée sur la **1ʳᵉ ligne**. Une
    image dépassant ``IMAGE_MAX_BYTES`` est **ignorée** (avertie), pas fatale.

    ``loader`` (``(dataset_id, split) → itérable de lignes``) est injectable pour
    tester sans la lib ``datasets`` ; défaut = streaming réel.
    """
    load = loader or _default_loader
    validated = False
    count = 0
    for row in load(dataset_id, split):
        if not isinstance(row, dict):
            continue
        if not validated:
            _validate_columns(row)
            validated = True
        image_bytes, ext = _extract_image(row[XEROCR_IMAGE_COLUMN])
        if len(image_bytes) > IMAGE_MAX_BYTES:
            logger.warning(
                "[huggingface] image > %d octets ignorée (dataset %s).",
                IMAGE_MAX_BYTES,
                dataset_id,
            )
            continue
        gt_value = row.get(XEROCR_GT_COLUMN)
        gt_text = gt_value if isinstance(gt_value, str) else ""
        yield HFPage(image_bytes=image_bytes, image_ext=ext, gt_text=gt_text)
        count += 1
        if limit is not None and count >= limit:
            return


__all__ = [
    "HF_API_BASE",
    "XEROCR_GT_COLUMN",
    "XEROCR_IMAGE_COLUMN",
    "HFPage",
    "HuggingFaceCatalogue",
    "HuggingFaceConventionError",
    "HuggingFaceDataset",
    "HuggingFaceUnavailableError",
    "search_reference",
    "stream_pages",
]
