"""Exceptions du domaine.

Hiérarchie centrée sur ``XerOCRError`` : un caller peut attraper toute
erreur métier XerOCR avec un seul ``except``.

Règle : ne jamais attraper ``XerOCRError`` dans le code métier sans la
re-lever — c'est le rôle de la couche transport (``app`` puis
``interfaces``) de mapper ces erreurs vers HTTP 4xx / sortie CLI.

Hiérarchie volontairement plate : on ajoute une sous-classe quand un
caller a besoin de discriminer.
"""

from __future__ import annotations


class XerOCRError(Exception):
    """Racine de la hiérarchie d'erreurs métier de XerOCR."""


class ArtifactValidationError(XerOCRError):
    """Un artefact ne respecte pas les invariants de son type."""


class ProjectionError(XerOCRError):
    """Un projecteur ne peut pas convertir l'artefact source.

    Le caller doit propager cette erreur dans le rapport de projection
    plutôt que de l'absorber silencieusement.
    """


class CorpusSpecError(XerOCRError):
    """Le ``CorpusSpec`` est mal formé (id dupliqués, GT incohérente…)."""


class AdapterStepError(XerOCRError):
    """Racine commune des erreurs d'adapter (OCR / LLM / VLM).

    Permet à un caller (typiquement l'executor) d'attraper « toute
    erreur d'adapter » sans connaître la sous-classe spécifique.
    """


class DeadlineExceeded(AdapterStepError):
    """Un adapter a détecté l'expiration de la ``Deadline`` reçue.

    Levée par un adapter qui respecte coopérativement la deadline
    propagée. Distincte des autres ``AdapterStepError`` pour permettre au
    runner de distinguer un timeout coopératif d'un échec fonctionnel.

    Un adapter doit lever ``DeadlineExceeded`` quand :

    - sa boucle interne détecte ``context.deadline.is_expired()`` avant
      d'avoir fini ;
    - son SDK lève un ``TimeoutError`` parce qu'on lui a passé
      ``context.deadline.as_sdk_timeout()`` qui s'est déclenché
      (l'adapter wrap et re-lève en ``DeadlineExceeded``).

    Un adapter ne doit PAS lever ``DeadlineExceeded`` pour un timeout SDK
    non lié à la deadline, ni pour une expiration côté serveur (504) →
    ``AdapterStepError`` standard.
    """


class RunCancelledError(XerOCRError):
    """Levée quand une cancellation coopérative a été signalée.

    Distincte de ``DeadlineExceeded`` : la cancellation est un signal
    explicite du caller (utilisateur, deadline globale du run), pas une
    expiration de la deadline du document en cours.
    """


class FormatError(XerOCRError):
    """Racine des erreurs de lecture/écriture d'un format documentaire.

    Permet à un caller (chargeur de corpus, projecteur) d'attraper « toute
    erreur de format » sans connaître le format précis. Les sous-classes
    spécifiques (``AltoParseError``, ``PageParseError``) vivent dans leur
    module de format (couche 2).
    """


__all__ = [
    "XerOCRError",
    "ArtifactValidationError",
    "ProjectionError",
    "CorpusSpecError",
    "AdapterStepError",
    "DeadlineExceeded",
    "RunCancelledError",
    "FormatError",
]
