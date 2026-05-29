"""``CorpusSpec`` — description immuable et déclarative d'un corpus.

Construit par un adapter de corpus, consommé par les services
applicatifs et le pipeline. Minimaliste : il décrit la structure (liste
de documents + métadonnées). Le chargement, le parsing et la détection
des patterns de nommage GT vivent ailleurs.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from xerocr.domain.documents import DocumentRef


class CorpusSpec(BaseModel):
    """Description immuable d'un corpus à benchmarker.

    Ne contient pas la racine du filesystem : les URIs des documents sont
    résolubles sans contexte, ce qui permet à un service de réécrire les
    chemins (sandbox, cache) sans muter le ``CorpusSpec``.

    Attributs
    ---------
    name:
        Nom court (rapports, cache, logs).
    documents:
        Liste ordonnée des ``DocumentRef`` ; ids uniques.
    metadata:
        Dictionnaire libre de contexte (``language``, ``period``,
        ``source``…). Pas de validation stricte sur les clés.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    documents: tuple[DocumentRef, ...] = Field(default_factory=tuple)
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("documents")
    @classmethod
    def _validate_unique_doc_ids(
        cls, v: tuple[DocumentRef, ...],
    ) -> tuple[DocumentRef, ...]:
        seen: set[str] = set()
        for doc in v:
            if doc.id in seen:
                from xerocr.domain.errors import CorpusSpecError

                raise CorpusSpecError(
                    f"document id dupliqué : {doc.id!r}. Les id de DocumentRef "
                    "doivent être uniques au sein d'un CorpusSpec."
                )
            seen.add(doc.id)
        return v

    def __len__(self) -> int:
        return len(self.documents)

    def doc_by_id(self, doc_id: str) -> DocumentRef | None:
        """Retourne le ``DocumentRef`` correspondant ou ``None``."""
        for doc in self.documents:
            if doc.id == doc_id:
                return doc
        return None


__all__ = ["CorpusSpec"]
