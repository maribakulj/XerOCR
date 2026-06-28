#!/usr/bin/env python3
"""Publie un **layout dataset canonique Cinoc** (produit par
``cinoc.app.dataset_standardize.standardize_corpus``) en **dataset Hugging Face**.

C'est l'étape **P3-b.3** : elle vit dans ``scripts/`` (≠ package ``cinoc``) car
elle dépend de ``huggingface_hub`` et fait un **effet de bord réseau credential-isé**
(upload + token write) — hors des 8 couches et hors de la CI.

À lancer **sur ta machine** (réseau + droit d'écriture HF ; le sandbox Cinoc
bloque ``huggingface.co``) :

    pip install huggingface_hub          # ou : pip install -e ".[huggingface]"
    export HF_TOKEN=hf_xxx               # token *write* (settings/tokens sur HF)
    python scripts/publish_dataset.py <layout_dir> <repo_id> [--private] [-m MSG]

Exemple :

    python scripts/publish_dataset.py ./dresden_out Ma-Ri-Ba-Ku/dresdner-hofdiarium

En sortie : l'URL du dataset, la **révision (SHA)** du commit, et l'appel
``import_curated_corpus(...)`` prêt à coller — épingle le SHA dans le
``RunManifest`` (reproductibilité).

⚠️ Pour la saveur de rapport « réfs IIIF/HF » (images affichées via liens), le
dataset doit être **public** : les ``resolve/<sha>/…`` d'un dataset privé exigent
un token et ne s'afficheront pas dans un rapport partagé (cf. VISION_DATASET §7).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publie un layout dataset canonique Cinoc sur Hugging Face.",
    )
    parser.add_argument("layout_dir", help="Dossier produit par standardize_corpus.")
    parser.add_argument("repo_id", help="Dataset HF cible, ex. 'org/nom-dataset'.")
    parser.add_argument(
        "--private", action="store_true", help="Crée un dataset privé "
        "(incompatible avec la saveur rapport « liens HF » publique)."
    )
    parser.add_argument(
        "-m", "--message", default="Publish Cinoc reference corpus",
        help="Message de commit.",
    )
    args = parser.parse_args()

    layout = Path(args.layout_dir)
    manifest = layout / "corpus.json"
    if not manifest.is_file():
        _eprint(f"erreur : layout invalide, {manifest} introuvable.")
        _eprint("(attendu : la sortie de standardize_corpus — corpus.json + iiif/ + …)")
        return 2

    try:
        from huggingface_hub import HfApi
        from huggingface_hub.utils import HfHubHTTPError
    except ImportError:
        _eprint("erreur : huggingface_hub absent. `pip install huggingface_hub`.")
        return 2

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    api = HfApi(token=token)
    try:
        who = api.whoami()
    except HfHubHTTPError as exc:
        _eprint(f"erreur d'authentification HF : {exc}")
        _eprint("→ `export HF_TOKEN=hf_xxx` (write) ou `huggingface-cli login`.")
        return 1
    print(f"authentifié comme : {who.get('name', '?')}")

    parsed = json.loads(manifest.read_text(encoding="utf-8"))
    doc_count = len(parsed.get("documents", []))
    print(f"layout : {layout}  ({doc_count} documents)")
    print(f"cible  : dataset {args.repo_id}  (private={args.private})")

    api.create_repo(
        repo_id=args.repo_id, repo_type="dataset",
        private=args.private, exist_ok=True,
    )
    commit = api.upload_folder(
        folder_path=str(layout), repo_id=args.repo_id, repo_type="dataset",
        commit_message=args.message,
    )

    revision = getattr(commit, "oid", None) or "main"
    base_url = f"https://huggingface.co/datasets/{args.repo_id}/resolve/{revision}"
    print("\n✅ publié.")
    print(f"   dataset  : https://huggingface.co/datasets/{args.repo_id}")
    print(f"   révision : {revision}")
    print(f"   base_url : {base_url}")
    print("\n— à coller pour un run épinglé (reproductible) —")
    print("from cinoc.app.corpus_import import import_curated_corpus")
    print(
        f"corpus = import_curated_corpus(\n"
        f"    '<snapshot local du dataset>',\n"
        f"    base_url={base_url!r},\n"
        f"    revision={revision!r},\n"
        f")"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
