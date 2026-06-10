"""Couche 1 — Domain.

Types purs et abstractions du modèle métier de XerOCR. Ce cercle
n'importe que la stdlib, ``pydantic`` et ``pydantic_core``. Il ne dépend
d'aucun moteur OCR, d'aucune métrique calculée, d'aucun rendu, d'aucune
couche réseau.

Règle d'or : si tu hésites à mettre quelque chose ici, c'est qu'il ne
devrait pas y être. Le domain ne fait presque rien — il décrit.

Note : ``RunResult`` / ``RunDocumentResult`` ne sont PAS ici — ils
agrègent des objets de couches plus externes (``evaluation``,
``pipeline``). Le domain ne décrit que des contrats.
"""

from __future__ import annotations

from xerocr.domain.artifact_key import ArtifactKey
from xerocr.domain.artifacts import Artifact, ArtifactType, compute_content_hash
from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.deadline import Deadline
from xerocr.domain.documents import DocumentRef, GroundTruthRef
from xerocr.domain.errors import (
    AdapterStepError,
    ArtifactValidationError,
    CorpusSpecError,
    DeadlineExceeded,
    ProjectionError,
    RunCancelledError,
    XerOCRError,
)
from xerocr.domain.evaluation import EvaluationSpec, EvaluationView, MetricSpec
from xerocr.domain.pipeline import (
    INITIAL_STEP_ID,
    PipelineMode,
    PipelineSpec,
    PipelineStep,
)
from xerocr.domain.projection import ProjectionSpec
from xerocr.domain.provenance import ProvenanceRecord
from xerocr.domain.run import RunManifest, utcnow
from xerocr.domain.usage import ResourceUsage

__all__ = [
    # Artifacts
    "Artifact",
    "ArtifactType",
    "compute_content_hash",
    "ArtifactKey",
    # Corpus + documents
    "CorpusSpec",
    "DocumentRef",
    "GroundTruthRef",
    # Timeout
    "Deadline",
    # Provenance
    "ProvenanceRecord",
    # Errors
    "XerOCRError",
    "ArtifactValidationError",
    "ProjectionError",
    "CorpusSpecError",
    "AdapterStepError",
    "DeadlineExceeded",
    "RunCancelledError",
    # Evaluation contracts
    "MetricSpec",
    "EvaluationView",
    "EvaluationSpec",
    "ProjectionSpec",
    # Pipeline spec
    "PipelineSpec",
    "PipelineStep",
    "PipelineMode",
    "INITIAL_STEP_ID",
    # Run manifest
    "RunManifest",
    "utcnow",
    # Ressources mesurées
    "ResourceUsage",
]
