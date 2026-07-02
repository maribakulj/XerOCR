"""Loader YAML → ``RunSpec`` (couche 6).

Un run est décrit par un fichier YAML, **validé** par Pydantic
(``RunSpec.model_validate`` — ``extra="forbid"`` rejette les clés inconnues),
puis dont les **chemins sont sécurisés** (``validated_path``, relatifs au dossier
du fichier ou à ``base_dir``). **Aucune résolution de classe d'adapter** ici : le
registre résout ``adapter_name → Module`` au runtime (journal D-010) — donc pas
d'import de chemin pointé arbitraire.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from cinoc.app.security import validated_path
from cinoc.domain.documents import DocumentRef
from cinoc.domain.errors import CinocError
from cinoc.domain.run_spec import RunSpec


class RunSpecError(CinocError):
    """Le fichier de run est illisible ou ne décrit pas un ``RunSpec`` valide."""


def load_run_spec(
    path: str | Path, *, base_dir: str | Path | None = None
) -> RunSpec:
    """Charge un ``RunSpec`` depuis un YAML, chemins sécurisés sous ``base_dir``."""
    yaml_path = Path(path)
    base = Path(base_dir) if base_dir is not None else yaml_path.parent
    try:
        raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise RunSpecError(f"YAML illisible : {exc}.") from exc
    if not isinstance(raw, dict):
        raise RunSpecError("YAML : un objet est attendu à la racine.")
    try:
        spec = RunSpec.model_validate(raw)
    except ValidationError as exc:
        raise RunSpecError(f"RunSpec invalide : {exc}.") from exc
    return _secure_paths(spec, base)


def _secure_paths(spec: RunSpec, base: Path) -> RunSpec:
    documents = tuple(_secure_document(doc, base) for doc in spec.corpus.documents)
    corpus = spec.corpus.model_copy(update={"documents": documents})
    return spec.model_copy(update={"corpus": corpus})


def _secure_document(document: DocumentRef, base: Path) -> DocumentRef:
    # Une image **distante** (corpus curé : référence http/https épinglée) passe
    # telle quelle — l'orchestrateur la matérialise au run via le fetch durci
    # (anti-SSRF + plafond). ``validated_path`` ne garde que les chemins locaux.
    raw_image = document.image_uri
    if raw_image is not None and raw_image.startswith(("http://", "https://")):
        image_uri: str | None = raw_image
    else:
        image_uri = (
            str(validated_path(raw_image, base)) if raw_image is not None else None
        )
    # La vérité-terrain est lue par l'évaluation : exiger son existence dès le
    # chargement donne une erreur claire (RunSpecError) au lieu d'un OSError
    # opaque en plein run. L'image, elle, n'est pas exigée ici — certains modules
    # (precomputed) ne la lisent pas, et tesseract signale clairement son absence.
    ground_truths = tuple(
        truth.model_copy(
            update={"uri": str(validated_path(truth.uri, base, must_exist=True))}
        )
        for truth in document.ground_truths
    )
    return document.model_copy(
        update={"image_uri": image_uri, "ground_truths": ground_truths}
    )


__all__ = ["RunSpecError", "load_run_spec"]
