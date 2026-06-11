"""``DocumentRef`` et ``GroundTruthRef``.

Référence à un document du corpus + ses vérités terrain multi-niveaux.
Ne porte pas le contenu : juste les chemins/URIs et les types. Le contenu
est chargé à la demande par les adapters de format.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from xerocr.domain.artifacts import ArtifactType

# Identifiant de document : alphanum + ``_.-/`` (les ``/`` permettent les
# hiérarchies type ``volA/folio_001``). Pas d'espaces, pas de caractères
# de contrôle.
_DOC_ID_RE = re.compile(r"^[A-Za-z0-9_.\-/]+$")


class GroundTruthRef(BaseModel):
    """Pointeur vers une vérité terrain pour un niveau donné.

    Distinct du contenu : on charge le fichier à la demande via l'adapter
    de format approprié.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: ArtifactType
    uri: str = Field(min_length=1, max_length=2048)


class DocumentRef(BaseModel):
    """Référence immuable à un document du corpus.

    Attributs
    ---------
    id:
        Identifiant unique dans le corpus (nom de fichier sans extension,
        ou chemin relatif ``volA/folio_001``).
    image_uri:
        Chemin vers l'image source. ``None`` pour les documents purement
        textuels.
    ground_truths:
        Vérités terrain disponibles, une par niveau (type unique).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1, max_length=256)
    image_uri: str | None = Field(default=None, max_length=2048)
    ground_truths: tuple[GroundTruthRef, ...] = Field(default_factory=tuple)
    #: Métadonnées libres par document (analogue documentaire de
    #: ``CorpusSpec.metadata``). Clé conventionnelle ``"stratum"`` = strate du
    #: document (genre/période/écriture), si la source la fournit. Optionnel :
    #: les consommateurs (composition, filtres, CER/strate) ne s'affichent que
    #: si présent. Renseigné par les importeurs/corpus, jamais figé.
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def _validate_doc_id(cls, v: str) -> str:
        if not _DOC_ID_RE.match(v):
            from xerocr.domain.errors import CorpusSpecError

            raise CorpusSpecError(
                f"document id invalide : {v!r}. Doit matcher {_DOC_ID_RE.pattern!r}."
            )
        # Défense en profondeur path-traversal : un segment ``..`` ou un
        # chemin absolu permettrait d'écrire hors workspace via la
        # résolution de chemin en aval (``Path(root) / id`` est réinitialisé
        # par un id absolu). Un doc_id légitime est toujours relatif.
        if v.startswith("/") or ".." in v.split("/"):
            from xerocr.domain.errors import CorpusSpecError

            raise CorpusSpecError(
                f"document id non relatif ou avec segment '..' : {v!r}. "
                "Path traversal rejeté."
            )
        return v

    @field_validator("ground_truths")
    @classmethod
    def _validate_unique_gt_types(
        cls, v: tuple[GroundTruthRef, ...],
    ) -> tuple[GroundTruthRef, ...]:
        seen: set[ArtifactType] = set()
        for gt in v:
            if gt.type in seen:
                from xerocr.domain.errors import CorpusSpecError

                raise CorpusSpecError(
                    f"GT dupliquée pour le type {gt.type.value!r}. "
                    "Un document ne peut avoir qu'une seule GT par niveau."
                )
            seen.add(gt.type)
        return v

    def gt_for(self, artifact_type: ArtifactType) -> GroundTruthRef | None:
        """Retourne la GT du niveau demandé, ou ``None``."""
        for gt in self.ground_truths:
            if gt.type == artifact_type:
                return gt
        return None

    @property
    def available_gt_types(self) -> tuple[ArtifactType, ...]:
        """Niveaux de GT disponibles, dans l'ordre d'insertion."""
        return tuple(gt.type for gt in self.ground_truths)


__all__ = ["DocumentRef", "GroundTruthRef"]
