# PLAN_IMAGES_SCALE.md — Benchmark à grande échelle (4000+) + images en dossier

> Plan **prospectif**. Objectif : exécuter un benchmark de **milliers de documents
> avec images réelles** dans un **dossier séparé** (HTML léger), **rapidement**
> (runner parallèle), **sans pénaliser** l'évolution future vers un **corpus IIIF
> dans un dataset HuggingFace**.
>
> **Autorité de statut = roll-up de [`MIGRATION_PLAN.md`](MIGRATION_PLAN.md).** Ce
> fichier ne déclare aucun « fait » ; chaque tranche livrée réconcilie le roll-up
> + le journal dans le même commit.

---

## Faits établis (vérifiés dans le code, juin 2026)

- **Moteur d'exécution unique** : web (`app.jobs.JobRunner`) **et** CLI
  (`interfaces/cli`) passent tous deux par `app.orchestrator.run`. → une évolution
  du runner profite aux deux.
- **Cap d'upload** `MAX_ENTRIES=1000` / `MAX_ZIP_BYTES=25 Mo` /
  `MAX_TOTAL_UNCOMPRESSED=200 Mo` : vit dans `extract_corpus_zip`
  (`app/corpus_upload.py`), appelé **uniquement** par l'endpoint d'**upload ZIP
  web** `POST /api/corpus`. Cet endpoint tourne à l'identique sur le **Space HF**
  et en **local** (`xerocr serve`). → le cap pénalise **les deux** déploiements
  web ; il **ne s'applique pas** à la **CLI** (corpus depuis fichiers locaux via
  spec YAML) ni aux **importeurs distants**.
- **Importeurs distants** (IIIF/Gallica/eScriptorium/HF) : **gated `403` en mode
  public** (`routers/corpus.py`). → indisponibles sur le Space public ; utilisables
  **en local/privé** seulement.
- **Importeur HF** (`import_hf_corpus`) : **streamé page-par-page**, `limit`
  paramétrable, **sans le cap des 1000** (ce cap est propre au ZIP).
- **Images au rapport** : résolues à la génération depuis `RunDocumentResult.image_ref`
  (un **URI générique** : chemin local **ou** URL) via `app/report_images.py` →
  vignettes **data-URI base64 inline**, plafonnées (300 vignettes / 60 fac-similés).
  Le **renderer est agnostique** de la provenance du href (`<img src="{href}">`).
- **Runner** : `orchestrator.run` est **séquentiel mono-thread**
  (`for pipeline: for document:`). Chaque unité `(pipeline, document)` est
  **indépendante** : sous-dossier workspace par pipeline + fichiers de sortie
  nommés par `document_id` (`workspace_artifact_path`, stem injectif) → aucune
  collision entre documents concurrents.

**Le Space n'est pas la machine de calcul** : free-tier 2 vCPU, disque éphémère,
cold-start, conteneur recyclé après inactivité, timeouts de requête. Un run de
4000 pages ne **planterait pas** (Python) mais **ne se terminerait pas** (timeout
/ recyclage). Les gros runs se font **en local** ; le Space reste vitrine.

---

## Principe directeur — un seul *seam* image (pour ne pas bloquer IIIF/HF)

Le renderer rend déjà `<img src="{href}">` depuis un mapping `{doc_id: href}` reçu
en intrant. On introduit **une seule** abstraction (couche 6) : une **stratégie de
résolution** qui produit ce mapping, et qui **branche sur le schéma** de
`image_ref` (chemin local vs URL IIIF vs URL directe). Dossier, IIIF et servi
partagent **le même seam** → l'évolution IIIF est **additive**, pas une réécriture.

| Saveur | `image_ref` | Produit | Hors-ligne | État |
|---|---|---|---|---|
| **Embedded** (fichier unique) | chemin local | data-URI base64 (plafonné) | ✅ | ✅ existe |
| **Sidecar / Dossier** | chemin local | dérivé dans `report-assets/`, href **relatif** | ✅ | 🆕 |
| **IIIF** | URL IIIF | `…/full/400,/0/default.jpg` (0 download) | ❌ | 🔮 additif |
| **Remote / HF** | URL directe | `<img src>` distant | ❌ | 🔮 additif |

---

## Tranches (internal→external, une par session)

### I2 — Runner parallèle (couche 4/6) — *en cours / livré dans ce plan*
Pool de threads borné sur la grille `(pipeline × document)`. **Threads** (pas
process) : OCR Tesseract = sous-processus, cloud = I/O HTTP → travail hors-GIL,
speedup quasi-linéaire sans sérialiser les artefacts. **Déterminisme** : exécution
parallèle, **assemblage dans l'ordre du spec** → `RunResult` byte-identique au
séquentiel (prouvé par test N=1 vs N=4). `max_workers` paramétrable
(`XEROCR_MAX_WORKERS` / `--workers`), défaut `os.cpu_count()`. Annulation/timeout
coopératifs conservés (`RunControl`/`Deadline`) ; isolation d'erreur par unité ;
`ResumeStore` accédé **main-thread** (pas de souci de concurrence).

### I0 — Poser le seam image (couche 5/6), **no-op**
Factoriser le cœur Pillow (`_render_jpeg`) ; exprimer l'existant comme
`resolve_facsimiles(result, strategy="embedded", …)`. Sortie inchangée → goldens
stables.

### I1 — Saveur Dossier + CLI `--report-dir` (couche 5/6/8)
`thumbnail_to_file(...)` (écrit le dérivé, href relatif) ; `strategy="sidecar"`
(caps relâchés — octets sur disque) ; `write_report_bundle(result, out_dir)` →
`report.html` + `report-assets/`. Renderer **inchangé**.

### I3 — Caps d'ingestion liés au déploiement (couche 6/8)
Transformer les caps d'upload en **paramètres résolus selon `public_mode`** :
**serrés sur le Space** (public, anti-abus), **relevés/configurables en local**.
*(La CLI n'en a pas besoin — pas de cap.)*

### I4 — Saveur réfs IIIF / dataset HF (couche 6) — *futur, dépend du dataset P3*
Branche `strategy="iiif"`/`"remote"` du seam I0/I1. Additif, petit. **Anti-spéculatif :
ne pas coder avant que le dataset P3 existe** (garde-fou « pas de consommateur »).

```
I0 (seam, no-op) ─→ I1 (Dossier + CLI)        → images en dossier
I2 (runner //)   ─────────────────────────────→ vitesse (web+CLI)
I3 (caps ingest) ─────────────────────────────→ 4000 via UI web locale
I4 (IIIF/HF) ⟸ I0/I1 + dataset P3 (futur)     → évolution HF, additive
```

**Chemin le plus court vers « 4000 + images dossier » aujourd'hui** : **CLI**
(pas de cap d'ingestion) + I1 + I2. I3 n'est requis que pour l'UI web.

---

## Garde-fous
- **Déterminisme prouvé** : goldens byte-identiques (runner // **et** HTML à hrefs
  relatifs).
- **Anti-spéculatif** : I4 (IIIF) seulement quand le dataset P3 existe.
- **Une tranche/session** + réconciliation journal (`D-146…`) au même commit.
- **Budgets fichier** respectés ; pas de second chemin d'exécution.
