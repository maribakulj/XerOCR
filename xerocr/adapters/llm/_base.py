"""Helpers partagés des adapters LLM (post-correction texte, mode ``text_only``).

Charge le texte OCR amont (``RAW_TEXT``), formate le prompt, **normalise** la
réponse du SDK (``str`` ou liste de blocs), écrit le ``CORRECTED_TEXT`` dans le
workspace. Les adapters concrets (openai, ollama…) implémentent le ``Module``
Protocol et n'ont qu'à fournir l'appel réseau — **isolé, mockable**.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from xerocr.adapters._workspace import workspace_artifact_path
from xerocr.domain.artifacts import Artifact, ArtifactType, compute_content_hash
from xerocr.domain.errors import AdapterStepError
from xerocr.formats.text import read_plaintext

#: Prompt de post-correction par défaut ; ``{ocr_text}`` est substitué.
DEFAULT_CORRECTION_PROMPT = (
    "Tu es un correcteur de transcriptions OCR de documents patrimoniaux. "
    "Corrige uniquement les erreurs manifestes de reconnaissance, sans "
    "reformuler ni moderniser l'orthographe historique. Réponds par le seul "
    "texte corrigé.\n\n{ocr_text}"
)


def normalize_llm_content(raw: Any) -> str:
    """Aplati une réponse LLM (``str`` ou liste de blocs) en chaîne."""
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        parts: list[str] = []
        for chunk in raw:
            if isinstance(chunk, str):
                parts.append(chunk)
            elif isinstance(chunk, dict) and isinstance(chunk.get("text"), str):
                parts.append(chunk["text"])
            else:
                text = getattr(chunk, "text", None)
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return str(raw)


def validate_llm_label(label: str, adapter: str) -> str:
    """Valide un label d'adapter LLM (alphanum + ``_ -``) et le renvoie.

    Le label compose le ``name`` du module (``<kind>:<label>``) ; le restreindre
    garde les noms de modules sûrs et stables (provenance ``RunManifest``).
    """
    if not label or not all(c.isalnum() or c in "_-" for c in label):
        raise AdapterStepError(
            f"{adapter} : label invalide {label!r} (alphanum + _ -)."
        )
    return label


def build_prompt(template: str, ocr_text: str) -> str:
    return template.replace("{ocr_text}", ocr_text)


def load_ocr_text(inputs: dict[ArtifactType, Artifact], adapter_name: str) -> str:
    artifact = inputs.get(ArtifactType.RAW_TEXT)
    if artifact is None or artifact.uri is None:
        raise AdapterStepError(
            f"{adapter_name} : input RAW_TEXT manquant ou sans URI."
        )
    return read_plaintext(Path(artifact.uri).read_bytes())


def write_corrected(
    workspace_uri: str,
    document_id: str,
    label: str,
    adapter_name: str,
    text: str,
) -> dict[ArtifactType, Artifact]:
    output_path = workspace_artifact_path(
        workspace_uri, document_id, label, "corrected.txt"
    )
    output_path.write_text(text, encoding="utf-8")
    return {
        ArtifactType.CORRECTED_TEXT: Artifact(
            id=f"{document_id}:{adapter_name}:corrected_text",
            document_id=document_id,
            type=ArtifactType.CORRECTED_TEXT,
            uri=str(output_path),
            content_hash=compute_content_hash(text.encode("utf-8")),
        )
    }


__all__ = [
    "DEFAULT_CORRECTION_PROMPT",
    "build_prompt",
    "load_ocr_text",
    "normalize_llm_content",
    "validate_llm_label",
    "write_corrected",
]
