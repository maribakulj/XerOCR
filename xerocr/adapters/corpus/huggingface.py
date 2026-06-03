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
from dataclasses import dataclass
from urllib.parse import urlencode

from xerocr.adapters.corpus._http import DEFAULT_TIMEOUT, HttpFetchError, fetch_json

logger = logging.getLogger(__name__)

HF_API_BASE = "https://huggingface.co/api"


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
        return tuple(results[:limit])


__all__ = [
    "HF_API_BASE",
    "HuggingFaceCatalogue",
    "HuggingFaceDataset",
    "search_reference",
]
