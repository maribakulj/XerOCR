# Cinoc

**Banc d'essai déterministe de pipelines de transcription (OCR / HTR / VLM)
pour documents patrimoniaux.**

Cinoc compare des pipelines de transcription (OCR, HTR, VLM, OCR→LLM) sur des
corpus à **vérité-terrain** et produit un **verdict factuel chiffré** —
métriques + tests statistiques — sous la forme d'un **rapport HTML autonome**.
Aucun LLM ne rédige le rapport : chaque nombre est une fonction **auditable** des
données d'entrée.

## Invariants

- **Déterministe** : même spec + même corpus + même code → mêmes artefacts (hash
  identique), mêmes métriques, même rapport.
- **Reproductible** : chaque run porte un `RunManifest` (version du code,
  dépendances, binaires, empreinte des paramètres).
- **Anti-hallucination** : le rapport n'affiche que des chiffres et des tableaux
  bruts — aucune prose générée.
- **Sûr** : XML durci (`safe_parse_xml` : pas de DTD/DOCTYPE/entité externe),
  chemins utilisateur validés (anti-traversal), mode public *fail-closed* sur le
  Space (seul le socle gratuit s'exécute).

## Architecture — 8 couches concentriques

```
domain ← formats ← evaluation ← pipeline ← adapters ← app ← reports ← interfaces
```

Une couche n'importe que des couches plus internes (vérifié par les tests
d'architecture). Détail : [`CLAUDE.md`](CLAUDE.md) et
[`MIGRATION_PLAN.md`](MIGRATION_PLAN.md).

## Installation

```bash
pip install -e ".[dev]"            # cœur + outils de dev (Python ≥ 3.11)
pip install -e ".[dev,serve]"      # + interface web locale
```

Les dépendances lourdes sont des **extras optionnels** : un adapter est toujours
listé, mais signale clairement s'il faut installer son extra (et sa clé d'API)
plutôt que de planter.

| Brique | Extra | Notes |
|---|---|---|
| Tesseract (OCR) | `[tesseract]` | binaire `tesseract` requis |
| Kraken · Pero · Calamari (HTR/OCR local) | `[kraken]` `[pero]` `[calamari]` | non déployés au Space |
| OpenAI · Anthropic · Mistral · Ollama (LLM/VLM) | `[openai]` `[anthropic]` `[mistral]` `[ollama]` | clé d'API |
| Google Vision · Azure Document Intelligence | `[google]` `[azure]` | REST, clé d'API |
| Segmenteur PP-DocLayout (local) | `[segment]` | poids PaddleX |
| Segmenteur distant (HF) | `[serve]` | délégué à un endpoint object-detection |
| NER (entités nommées) | `[ner]` | spaCy + modèle (`spacy download …`) |
| Import / publication HuggingFace | `[huggingface]` | datasets + `huggingface_hub` |
| Vignettes réelles du rapport | `[images]` | Pillow (dégradé gracieux sans) |

## Démarrage rapide

```bash
cinoc demo --output rapport.html              # rapport de démonstration (sans moteur)
cinoc run config.yaml -o rapport.html         # exécute un run décrit en YAML
cinoc run config.yaml --report-dir bundle/    # rapport en dossier (HTML + images séparées)
cinoc run config.yaml --json run.json         # exporte aussi le RunResult (machine)
cinoc compare a.json b.json -o diff.html      # compare deux runs (deltas)
cinoc serve --port 8080                        # interface web locale
```

## Moteurs et modules (socle first-party)

- **OCR/HTR** : Tesseract, Kraken, Pero, Calamari, Mistral OCR, Google Vision,
  Azure Document Intelligence.
- **LLM (post-correction texte)** : OpenAI, Anthropic, Mistral, Ollama.
- **VLM (zero-shot ou image+texte)** : OpenAI, Anthropic, Mistral.
- **Segmentation** : PP-DocLayout (local) ou **segmenteur distant** (un modèle
  object-detection hébergé sur HuggingFace, sélectionnable avant le run — on
  change de modèle en changeant l'URL).
- **NER** : étape optionnelle `texte → entités` (spaCy), scorée si le corpus
  porte une vérité-terrain d'entités.

**Modes de pipeline OCR+LLM** : `zero_shot` (le VLM transcrit l'image
directement), `text_only` (OCR → LLM corrige le texte), `text_and_image` (OCR →
le VLM voit image + texte).

## Extension par modules tiers

Le **seul** point d'extension public = les **briques de pipeline** (segmenteur,
OCR/HTR, VLM, post-correcteur, NER…). Un paquet pip qui expose un entry-point
`cinoc.modules` est découvert au runtime (fail-closed en mode public). Tout le
reste (métriques, importeurs, sections de rapport, tests statistiques) est
first-party, non pluggable — une seule prise, par design.

## Bibliothèque de corpus

- **Upload ZIP** (glisser-déposer) ou **imports distants** : IIIF, Gallica,
  eScriptorium, HuggingFace.
- **Datasets curés Cinoc** publiés sur HuggingFace : import par identifiant +
  **découverte automatique** des datasets de ton compte (variable
  `CINOC_HF_AUTHOR` + tag `cinoc-corpus`) — les images restent des références
  IIIF épinglées à une révision, seuls le manifeste + la vérité-terrain sont
  rapatriés.

## Saveurs de rapport

| Saveur | Forme | Hors-ligne |
|---|---|---|
| Fichier unique | un `.html` (images base64 inline, plafonnées) | ✅ |
| Dossier / ZIP | `report.html` + `report-assets/` (images séparées) | ✅ |
| Réfs IIIF / HF | `.html` léger, images chargées depuis HuggingFace | ❌ |

Rapport **bilingue FR/EN** (`?lang=en` côté web). Les nombres **affichés** sont
localisés (virgule en français) ; les couches **machine** (export JSON/CSV,
`data-sort`) restent en point — pour toute consommation par un outil, utiliser
l'export JSON.

## Interface web / Space

```bash
cinoc serve                 # local
```

Déploiement HuggingFace Space : voir [`deploy/`](deploy/). Variables
d'environnement principales :

| Variable | Rôle |
|---|---|
| `CINOC_PUBLIC_MODE` | mode public *fail-closed* (socle gratuit seul) |
| `CINOC_REPORTS_DIR` · `CINOC_DATA_DIR` | dossiers rapports / runtime |
| `CINOC_HF_AUTHOR` | compte HF pour la découverte des datasets curés |
| `CINOC_MAX_WORKERS` · `CINOC_NETWORK_CONCURRENCY` | parallélisme / plafond réseau |
| `CINOC_METRICS` | expose `/metrics` (Prometheus), opt-in |

Clés d'API (selon moteurs) : `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
`MISTRAL_API_KEY`, `GOOGLE_VISION_API_KEY`, `AZURE_DOC_INTEL_ENDPOINT` /
`AZURE_DOC_INTEL_KEY`.

## Développement

```bash
make check-fast   # ruff + mypy + toute la suite (pré-push)
make lint         # ruff
make type         # mypy
make test         # pytest (parallèle)
make ci           # gate complet (avec couverture)
```

La CI GitHub Actions tourne sur Linux/macOS/Windows × Python 3.11/3.12/3.13 et
porte le seuil de couverture. Parcours détaillé et journal des décisions :
[`MIGRATION_PLAN.md`](MIGRATION_PLAN.md) · changements notables :
[`CHANGELOG.md`](CHANGELOG.md).
