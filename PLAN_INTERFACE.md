# PLAN_INTERFACE.md — Refonte de l'interface web XerOCR

> **Objet.** Plan d'exécution de la refonte UI « produit fini » : composeur
> OCR/LLM/VLM complet (3 modes, tous les fournisseurs), **runs multi-concurrents
> exposés au web**, parité fonctionnelle avec l'interface Picarones + ajouts propres
> à XerOCR (segmentation), et **système typographique à 3 familles**.
>
> **Garanties.** Zéro shim, zéro chemin parallèle, zéro création de fichier inutile.
> L'inventaire create-vs-modify ci-dessous a été **vérifié au contact du code**
> (références `fichier:ligne`). On construit par **tranches verticales** (CLAUDE.md §4),
> chacune verte de bout en bout (`make ci`).
>
> Doc périssable (design cible) au sens de CLAUDE.md §9 — à confirmer au build.
> Branche : `claude/nifty-hawking-P2GFL` (continue le travail « Étape 3 / Bibliothèque »).

---

## 1. Constat technique vérifié

### 1.1 Le cœur est **nativement multi-concurrent** — NE PAS y toucher
Le défaut majeur de Picarones (plusieurs **runs séparés** pour comparer des moteurs)
**n'est pas reproduit** dans XerOCR :

- `RunSpec.pipelines` = **tuple de N pipelines** (`domain/run_spec.py:28`, `min_length=1`).
- `orchestrator.run()` exécute les N pipelines sur **le même corpus**, dans **un seul
  run**, puis **une seule** évaluation → **un** `RunResult` couvrant tous les
  concurrents (`app/orchestrator.py:69`, `:88`, `:112`) → section `cross_engine`.
- Le commentaire d'isolation (`orchestrator.py:80-85`) **anticipe explicitement**
  plusieurs chaînes OCR→LLM concurrentes dans un seul run.
- Preuves bout-en-bout : `interfaces/demo.py:112` (`pipelines=pipelines`, N moteurs) +
  la CLI.

**Seul manque** : le *lanceur web* `run_planning.plan_ocr_run` (`:108`) prend **un**
moteur et bâtit une spec mono-pipeline, parce que le formulaire S6 ne poste qu'un
`engine`. C'est un trou de **surface**, pas d'architecture.

### 1.2 OCR→LLM : existe au moteur, partiel, non exposé web
| Brique | État XerOCR | Référence |
|---|---|---|
| Pipeline 2 étapes OCR→LLM + executor DAG | ✅ **testé** | `tests/app/test_orchestrator.py:92`, `tests/adapters/test_llm_pipeline.py:16` |
| Mode `text_only` (LLM corrige le texte) | ✅ | adapters llm `RAW_TEXT → CORRECTED_TEXT` |
| Mode `text_and_image` (le LLM voit l'image) | ❌ adapters texte seul | `adapters/llm/openai.py:87` |
| Mode `zero_shot` (VLM image→texte) | ❌ aucun adapter vision | — |
| Adapter Anthropic | ❌ (openai/ollama/mistral) | `app/modules/registry.py` |
| Exposition web | ❌ refus 422 | `interfaces/web/routers/runs.py:122` |

### 1.3 Le contrat est prêt pour **tout** le périmètre
- **Contrat unique** `Module` Protocol (`pipeline/protocols.py:36`), duck-typed, générique.
- `inputs_from` **pleinement générique** (`pipeline/executor.py:122`) : un step LLM peut
  recevoir **IMAGE** (`__initial__`) **et** **RAW_TEXT** (étape OCR) → `text_and_image`
  natif, sans bricolage.
- Registre + **découverte entry-points** `xerocr.modules` déjà en place (`app/modules/`).
- `PipelineMode` **déclaré** (`domain/pipeline.py:32`) mais **non consommé** → à brancher.

### 1.4 Cause de l'illisibilité (motivation Phase 0)
`shell.css:58-61` : `--sans` **et** `--mono` pointent sur **`OCRA`** → **tout le corps
de texte est rendu en OCR-A**. C'est la racine du « illisible ».

---

## 2. Décisions d'architecture (anti-chaos)

1. **Cœur intact.** Le multi-concurrent passe par le `runner.launch(SpecBuilder)`
   (`app/jobs.py:84`) et l'orchestrateur **déjà multi-pipeline** — aucun second chemin.
2. **Adapters : 1 fichier par fournisseur, rôle-aware — PAS 7 fichiers vision.**
   Rejet explicite du « 8+8+8 » proscrit par CLAUDE.md §8.8. Chaque fournisseur
   (`openai`/`anthropic`/`mistral`/`ollama`) = **un** adapter dont
   `input_types/output_types` sont fixés **à la construction** selon le `role`
   (`text_only` / `text_and_image` / `zero_shot`). Le multimodal (base64) est
   **factorisé dans `_base.py`**. → **un seul** nouvel adapter : `anthropic.py`.
3. **Contrat / format / spec uniques** : `Module` / `RunResult` / `RunSpec`
   **inchangés**.
4. **Zéro shim, zéro double représentation.**
5. **DTOs inline par routeur** (convention du repo) : le multi-concurrent **étend**
   `LaunchRequest` (`runs.py:46`) sur place — pas de module `schemas`.
6. **Pages rendues serveur** par `home.py` ; JS léger auto-hébergé (pas de SPA).

---

## 3. Système typographique (3 familles, auto-hébergées)

| Rôle | Police | Token | Livraison |
|---|---|---|---|
| Titres / hero / wordmark | **OCR-A** | `--display` | déjà là (`static/fonts/OCRA.woff2`) |
| Sous-titres / accents | **Fluxisch Else** | `--accent` | déjà là (`FluxischElse-*.woff2`) |
| Corps / UI / contrôles | **IBM Plex Sans** (400/500/600) | `--sans` | **woff2 à ajouter** |
| Données (CER %, IDs, code) | **IBM Plex Mono** (400/500) | `--mono` | **woff2 à ajouter** |

Contrainte CSP `font-src 'self'` : **aucun CDN**, woff2 auto-hébergés sous
`static/fonts/`. Fallback `system-ui`/`ui-monospace` si un woff2 manque (jamais cassé).

---

## 4. Ce qui existe déjà → **NE PAS recréer** (corrections de la vérif)

| Prévu initialement | Réalité vérifiée | Décision |
|---|---|---|
| Endpoint normalisation + câblage couche 3 | `evaluation/runner.py:281` applique **déjà** `view.normalization_profile` (symétrique GT/hyp) | **Aucun** code couche 3 ni endpoint ; passer le profil à la vue dans `run_planning`, profils injectés au template par `home.py` |
| Endpoint « Découvrir » (HTR-United / HF) | `home.py:180-188` fetch **déjà** `fetch_catalogue` + `HuggingFaceCatalogue().search(q)` (cache TTL, repli démo) | **Aucun** endpoint ; styler `library.html` |
| `GET /api/engines` | **existe** (`routers/engines.py:19`) | **Étendre** `EngineStatus` (couche 6), pas de route neuve |
| Module `schemas` pour le multi-concurrent | DTOs **inline par routeur** (`LaunchRequest`, `runs.py:46`) | **Étendre** `LaunchRequest` sur place |
| Polices à intégrer | OCR-A + Fluxisch Else **déjà auto-hébergées** | **Ajouter seulement** IBM Plex |
| 7 fichiers vision | reproduit le « 8+8+8 » (§8.8) | **Rejeté** → modes dans les adapters existants + `anthropic.py` |
| Changement `domain` / `evaluation` | `PipelineMode`, `inputs_from`, `RunSpec.pipelines` **déjà dimensionnés** | **Aucun** changement |

---

## 5. Inventaire définitif

### 5.1 CRÉER (minimum strict)
- `xerocr/adapters/llm/anthropic.py` — **seul** nouvel adapter (rôle-aware, 3 modes).
- `xerocr/interfaces/web/static/fonts/IBMPlexSans-{400,500,600}.woff2`,
  `IBMPlexMono-{400,500}.woff2`, `IBMPlex-LICENSE.txt` — assets.
- `tests/architecture/test_no_dead_ui.py` — garde-fou anti-vide.
- Tests par feature sous `tests/` (modes, multimodal, multi-concurrent, delete corpus).
- `PLAN_INTERFACE.md` — ce document (mémoire durable).

→ **Aucun** nouveau routeur, template, DTO, endpoint, ni fichier vision.

### 5.2 MODIFIER (par couche, à leur emplacement existant)
| Couche | Fichiers | Nature |
|---|---|---|
| **5 adapters** | `llm/_base.py` (+helpers image/base64) ; `llm/openai.py`, `llm/mistral.py` (rôle→modes) ; `llm/ollama.py` ; `llm/__init__.py` | extension, même contrat `Module` |
| **6 app** | `run_planning.py` (builders OCR→LLM & zero_shot ; `plan_benchmark_run` multi-pipeline ; profil de normalisation sur la vue ; **consolide** `plan_ocr_run`) ; `modules/registry.py` (+`_build_anthropic`, kwarg `role`) ; `engines.py` (`EngineStatus` capacités/modes + kinds anthropic/vlm) ; `corpus_upload.py` (+`delete`) |
| **8 routers** | `runs.py` (`LaunchRequest`→liste de concurrents + mode ; **retire** le 422 `LLM_KINDS` ; appelle `plan_benchmark_run`) ; `corpus.py` (+`DELETE /api/corpus/{id}`) ; `home.py` (injecte profils de normalisation + modes moteurs + séries d'historique) |
| **8 templates** | `base.html`, `home.html`, `benchmark.html`, `library.html`, `history.html`, `segmentation.html`, `engines.html` | refonte visuelle |
| **8 static** | `css/shell.css` (tokens + polices + composants) ; `js/benchmark.js` (file de concurrents + SSE) ; `js/corpus.js` (upload + delete + découverte) |
| **tests / meta** | `tests/guardrails/test_engine_dispatch_exhaustive.py` (migré vers `plan_benchmark_run`) ; `pyproject.toml` (+extra `anthropic`) ; `MIGRATION_PLAN.md` (roll-up / DoD — **vérifier** `test_status_freshness`) |

### 5.3 AUCUN changement
- `domain/` : `PipelineMode`, `inputs_from`, `RunSpec` déjà dimensionnés.
- `evaluation/` : normalisation déjà honorée (`runner.py:281`).

---

## 6. Phases (tranches verticales, chacune verte de bout en bout)

### Phase 0 — Design system (transverse)
- **MODIFIER** `static/css/shell.css` : tokens polices (rôles §3), palette, composants
  manquants (dropzone, cartes corpus, onglets, barres de stats, sparklines).
- **CRÉER** `static/fonts/IBMPlex*.woff2` + LICENSE ; `@font-face` IBM Plex dans
  `shell.css` ; fallback système.
- **DoD** : toutes les pages lisibles (corps en IBM Plex Sans), CSP respectée
  (aucun CDN). `make ci` vert.

### Phase 1 — Moteur : 3 modes × tous fournisseurs (couches 5-6)
- **CRÉER** `adapters/llm/anthropic.py` (rôle-aware).
- **MODIFIER** `_base.py` (+`load_image_b64`/`encode_image_base64`/prompt multimodal) ;
  `openai.py` + `mistral.py` (rôle→`text_only`/`text_and_image`/`zero_shot`) ;
  `ollama.py` (text_only) ; `registry.py` (+`_build_anthropic`, kwarg `role`) ;
  `run_planning.py` (`_ocr_llm_spec`, `_zero_shot_spec`, dispatcher consommant
  `PipelineMode`) ; `pyproject.toml` (+`anthropic`).
- **Tests** : chaque mode bout-en-bout via orchestrateur (SDK mockés) ; chaque adapter
  en isolation ; `PipelineMode` consommé.
- **DoD** : `xerocr run` couvre OCR seul / OCR→LLM texte / OCR→LLM image+texte / VLM
  zero-shot, avec openai·anthropic·mistral (+ollama texte).

### Phase 2 — Run multi-concurrent + exposition web (couche 6 + API)
- **MODIFIER** `run_planning.py` (`plan_benchmark_run(competitors, corpus, run_id)` →
  `RunSpec` à N pipelines ; helpers de pipeline par concurrent partagés) ; `runs.py`
  (`LaunchRequest` = liste de `Competitor` + mode ; **retire** `LLM_KINDS`/422 ; gating
  mode public par concurrent via `CLOUD_KINDS` ; `runner.launch(plan_benchmark_run(...))`) ;
  `engines.py` (modes par moteur) ; migrer
  `tests/guardrails/test_engine_dispatch_exhaustive.py`.
- **Tests** : POST HTTP de 2+ concurrents → **un** `RunResult` + cross-engine ; mode
  public → 403 cloud ; mode incohérent → 422.
- **DoD** : le web lance N concurrents dans **un seul** run comparé, tous modes.

### Phase 3 — Surface UI complète (couche 8, backends réels)
- **Bibliothèque** : `corpus.py` (+`DELETE /api/corpus/{id}`) + `corpus_upload.py`
  (`delete`) ; `library.html`/`corpus.js` : dropzone stylée, cartes corpus, CTA
  « Utiliser dans Benchmark », onglets « Mes corpus / Découvrir » (données déjà fournies
  par `home.py`).
- **Banc d'essai** : `benchmark.html`/`benchmark.js` : **file de concurrents**
  (add/remove) ; par concurrent : mode (OCR seul / OCR→LLM texte / image+texte / VLM
  zero-shot / Segmentation) + moteur/modèle/langue/fournisseur **pilotés par
  `/api/engines`** (seules les options réelles/disponibles s'affichent → anti-vide) ;
  sélecteur de normalisation (profils injectés par `home.py`, lus dynamiquement de
  `formats/text/normalization.py`) ; lancement SSE + progression live.
- **Historique** : `home.py` injecte les séries (`history_store.history`),
  `history.html` rend des **sparklines CER** (SVG inline déterministe).
- **Segmentation / Moteurs / Panneau système** : restyle `segmentation.html`,
  `engines.html` (statuts réels), panneau (moteurs X/Y, LLM X/Y, tâche active, mode).
- **DoD** : parité Picarones + ajouts XerOCR, chaque contrôle sur un backend réel.

### Phase 4 — Garde-fou anti-vide + docs + CI
- **CRÉER** `tests/architecture/test_no_dead_ui.py` : chaque mode×fournisseur ↔ builder
  enregistré + branche `run_planning` ; `engine_statuses` kinds ⊆ registre ; actions de
  formulaire ↔ routes existantes.
- **MODIFIER** `MIGRATION_PLAN.md` (roll-up / DoD), `pyproject.toml`.
- **Porte** : `make ci` complet vert avant push.

---

## 7. Ce que je NE fais pas (anti-bloat, explicite)
7 fichiers d'adapters vision · moteur narratif (supprimé en XerOCR) · shim / double
format · option UI sans backend (chaque option vient de `/api/engines`).

---

## 8. Vérification (porte, non négociable)
`make ci` (ruff + mypy + pytest **complet**) avant chaque push. Commits par phase sur
`claude/nifty-hawking-P2GFL`. Jamais « vert » sur un sous-ensemble (CLAUDE.md §11).
