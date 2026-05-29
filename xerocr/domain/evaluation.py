"""``MetricSpec``, ``EvaluationView``, ``EvaluationSpec``.

Comparer des pipelines hétérogènes en projetant leurs sorties vers une
vue d'évaluation explicite. On ne compare jamais directement un OCR brut
et une sortie ALTO reconstruite : on compare leur projection dans une vue
commune, et le rapport explicite ce que la vue ignore.

- ``MetricSpec`` — déclare une métrique (nom + signature de types).
  **Purement déclaratif** : pas de callable. L'association nom → fonction
  se fait dans le registre runtime (couche evaluation), pas ici.
- ``EvaluationView`` — déclare une vue (candidats + projection + métriques
  + dimensions ignorées).
- ``EvaluationSpec`` — container de N vues.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from xerocr.domain.artifacts import ArtifactType
from xerocr.domain.projection import ProjectionSpec


class MetricSpec(BaseModel):
    """Description déclarative d'une métrique enregistrable.

    Attributs
    ---------
    name:
        Identifiant unique dans un registre.
    input_types:
        Tuple ``(reference_type, hypothesis_type)`` ; le registre
        sélectionne les métriques applicables à une jonction par cette
        signature.
    higher_is_better:
        ``True`` pour les métriques de qualité (F1, recall), ``False``
        pour les métriques d'erreur (CER, WER).
    tags:
        Étiquettes libres pour grouper (``"text"``, ``"structure"``…).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    input_types: tuple[ArtifactType, ArtifactType]
    description: str = ""
    higher_is_better: bool = False
    tags: frozenset[str] = Field(default_factory=frozenset)


class EvaluationView(BaseModel):
    """Une vue d'évaluation = une lentille pour comparer des pipelines.

    Répond à : « lequel des pipelines produit la meilleure sortie sous cet
    angle ? » Un pipeline ne produisant aucun artefact dans
    ``candidate_types`` est omis explicitement (pas de score factice).

    ``projection`` s'applique à tous les candidats ;
    ``projections_by_source_type`` permet une projection conditionnelle
    par type source. ``char_exclude`` filtre des caractères APRÈS
    ``normalization_profile``. ``ignored_dimensions`` est affiché pour
    signaler ce que la comparaison ne dit pas.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    description: str = ""
    candidate_types: frozenset[ArtifactType] = Field(...)
    projection: ProjectionSpec | None = None
    projections_by_source_type: dict[ArtifactType, ProjectionSpec] = Field(
        default_factory=dict,
    )
    normalization_profile: str | None = Field(default=None, max_length=128)
    char_exclude: str | None = Field(default=None, max_length=512)
    metric_names: tuple[str, ...] = Field(default_factory=tuple)
    ignored_dimensions: tuple[str, ...] = Field(default_factory=tuple)
    warnings: tuple[str, ...] = Field(default_factory=tuple)

    def accepts(self, artifact_type: ArtifactType) -> bool:
        """Vrai si cette vue peut consommer un artefact du type donné."""
        return artifact_type in self.candidate_types

    def projection_for(
        self, source_type: ArtifactType,
    ) -> ProjectionSpec | None:
        """Projection à appliquer pour un artefact source donné.

        1. ``projections_by_source_type[source_type]`` si présent ;
        2. ``projection`` si son ``source_type`` matche ;
        3. ``None`` (artefact comparé tel quel).
        """
        if source_type in self.projections_by_source_type:
            return self.projections_by_source_type[source_type]
        if (
            self.projection is not None
            and self.projection.source_type == source_type
        ):
            return self.projection
        return None


class EvaluationSpec(BaseModel):
    """Container de N ``EvaluationView`` qu'un benchmark applique."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    views: tuple[EvaluationView, ...] = Field(default_factory=tuple)

    def view_by_name(self, name: str) -> EvaluationView | None:
        """Retourne la vue de nom ``name`` ou ``None``."""
        for v in self.views:
            if v.name == name:
                return v
        return None


__all__ = ["MetricSpec", "EvaluationView", "EvaluationSpec"]
