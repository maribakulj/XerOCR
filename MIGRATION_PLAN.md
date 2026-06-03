# Plan de migration XerOCR — par tranches verticales

> **Nature** : plan d'**enveloppe** transverse (séquencement des tranches + invariants
> de contrat). Complète les guides par couche (`xerocr/**/MIGRATION_COUCHE_*.md`,
> `xerocr/**/ANALYSE_COUCHE_*.md`) en les **reliant** en un parcours de bout en bout.
> **À lire avec** [`CLAUDE.md`](CLAUDE.md) (le contrat de travail : deux axes, 5 garde-fous).
>
> **Statut épistémique** (`CLAUDE.md` §9) : l'**enveloppe** (contrats, séquencement) est
> **durable** ; la **surface** (quelle métrique / route / module exactement) est
> **PROVISOIRE — à confirmer au build**. Le contact du code amont non encore mergé prévaut.

---

## Tableau de bord (roll-up) — état vivant

> **Source de vérité du détail = la `DoD vivante` de chaque `COUCHE` doc.** Ce
> tableau n'est qu'un **index** : il pointe, il ne recopie pas (sinon il dériverait).

**Légende tri-état** : `[x]` fait **+ preuve nommée** (test/commande/grep) · `[ ]` à faire ·
`[~]` **différé/réserve avec raison** (distinguer *différé-par-design* de *réserve-ouverte*).

| Couche / Tranche | État | DoD détaillée (autorité) |
|---|---|---|
| 1 `domain` | ✅ **vert** ; **+`CanonicalLayout`** (T5, type pivot mise en page neutre) **+`PipelineStep.fanout`** (T5, drapeau déclaratif reconnaissance par région) | `xerocr/domain/MIGRATION_COUCHE_1.md` §DoD |
| 2 `formats` | ✅ **vert** ; **+`alto/layout_map`** (T5, `alto_to_layout` + `layout_to_alto` ↔ neutre) **+`pagexml/layout_map`** (T5, `page_to_layout`) | `xerocr/formats/MIGRATION_COUCHE_2.md` §DoD |
| 3 `evaluation` | ✅ **T2** (CER/WER/MER · stats `scipy` · `cross_engine`) **+ T7 philologie/profil** (`cer_diplo` · `diacritic_err` · `del_rate`/`ins_rate` ; `rapidfuzz` en prod) **+ T5 structure** (`region_cer` · loader `LAYOUT` JSON+**ALTO**+**PAGE**) | `xerocr/evaluation/MIGRATION_COUCHE_3.md` §DoD |
| 4 `pipeline` | ✅ **T3** (Protocol + exécuteur · annulation câblée) ; **+`fanout`** (T5, reconnaissance par région + échec partiel) **+ exécuteur fan-out déclaratif** (`step.fanout` → `execute_region_fanout`, LAYOUT rempli persisté + estampillé) | `xerocr/pipeline/ANALYSE_COUCHE_4.md` §DoD |
| 5 `adapters` | ✅ **T3 complet** (`precomputed`+`tesseract`+`openai`+`ollama`) ; **+`storage/JobStore`** (journal SSE) **+`storage/publisher`** (S3, push GitHub opt-in) ; **+`layout/precomputed`** (T5, source LAYOUT + recognizer région) **+`layout/assembler`** (T5, `AltoAssembler` LAYOUT→ALTO_XML) | `xerocr/adapters/ANALYSE_COUCHE_5.md` §DoD |
| 6 `app` | ✅ **T2** (orchestrateur · loader/sécurité) ; **+`JobRunner`** (TU2.a, + hook publication S3) **+`CorpusStore`** (TU2.c) **+ builders segmentation** (T5 : `precomputed_layout` · `precomputed_region` · `alto_assembler`) | `xerocr/app/ANALYSE_COUCHE_6.md` §DoD |
| 7 `reports` | ✅ **T2** + **design complet** (S4.a→S4.b : chrome · polices data-URI · readouts/data-bars · by-engine · by-document · crosses ; synthesis différé T7) | `xerocr/reports/ANALYSE_COUCHE_7.md` §DoD |
| 8 `interfaces` | 🔨 **T4 socle ✅ · Space S1·S2·S3·S4 ✅** (vitrine · lanceur · persistance · vues rapport au design ; reste **S5**/S6) | `xerocr/interfaces/ANALYSE_COUCHE_8.md` §DoD |
### Les deux axes : **Moteur `T#`** & **Space `S#`** — un seul tableau, dépendances explicites

**Deux *natures* de travail, un seul tableau d'autorité.** `T#` = la
**bibliothèque déterministe** (couches 1–7, intérieur→extérieur). `S#` = l'**app
web interactive** (couche 8 + déploiement) qui **consomme** le moteur. Les arêtes
`⟸` sont des **dépendances** (un `S` ne peut aboutir que si son moteur est prêt) :
c'est un **ordre partiel**, pas deux files déconnectées.

| Axe **Moteur** `T#` | Livre | État |
|---|---|---|
| **T0** fondations | domain + formats | ✅ **clos** (§9) |
| **T1** squelette ambulant | `xerocr demo` octet-stable (3→8) | ✅ **fait** |
| **T2** axe texte | `tesseract` réel · CER/WER/MER · stats · `run`/`compare` | ✅ **fait** |
| **T3** OCR + LLM | pipeline 2 étapes · `openai`+`ollama` · annulation câblée | ✅ **fait** |
| **T4** socle web | `create_app` factory · package `security/` · vitrine **read-only** · Docker/Space | ✅ **fait** |
| **T5** structure / segmentation | `CanonicalLayout` · fan-out région · métrique `(LAYOUT,LAYOUT)` | 🔨 **squelette livré** (precomputed : LAYOUT régions-seules → fan-out → `region_cer` page → rapport, bout-en-bout) · **+ `alto_to_layout`** (GT layout ALTO réelle chargeable) · **+ assemblage `layout→ALTO_XML`** (`AltoAssembler`, contrat §3 bouclé) · **+ pipeline déclarative 3 étages** (une `PipelineSpec` : segment → fanout reconnaissance → assemblage, modules via factory) · **+ `page_to_layout`** (GT layout PAGE réelle chargeable ; sniff ALTO/PAGE) · **+ câblage données réelles** (4 producteurs réels chargés ; `region_cer` correct/non-trivial/non trompeur via le runner) · reste segmenteur réel + crop · alignement IoU · fetch BNL live (infra) |
| **T6** extensibilité tierce | entry-points `xerocr.modules` + 1 plugin de réf. | ⏳ |
| **T7** surfaces internes | importeurs cœur · longitudinal · philologie · métriques | 🔨 **partiel** : 3 métriques livrées — `cer_diplo` (#25) · `diacritic_err` (#26) · `del_rate`/`ins_rate` (#27), câblées sur le benchmark réel BNL · reste importeurs cœur · longitudinal · `synthesis` |

| Axe **Space** `S#` | Livre | Dépend de | État |
|---|---|---|---|
| **S1** coquille au design | rendu serveur · polices self-host · nav · FR/EN | T4 ✅ | ✅ **fait** |
| **S2** lanceur « Banc d'essai » | run de fond annulable · Moteurs `/api/engines` + page `/engines` · upload durci · gardes HTTP · SSE · page JS + **UI upload/sélection** | T2,T3,T4 ✅ | ✅ **fait** (run moteur réel = Space privé / test `live`) |
| **S3** persistance | push `RunResult` JSON → dépôt GitHub après run (opt-in secrets) | T4 ✅ | ✅ **fait** (best-effort · push réel = test `live`) |
| **S4** vues rapport au design | overview/by-engine/by-document/crosses/synthesis | couche 7 ✅ | 🔨 chrome + overview (S4.a) · polices data-URI (S4.b.1a) ✅ · readouts+data-bars (S4.b.1b) · by-document (S4.b.2) · by-engine (S4.b.3) · **crosses (S4.b.4)** ✅ — **fait** : toutes les vues au design + rapport autonome octet-stable ; **synthesis différé T7** |
| **S5** sécurité publique | mode public · quotas · rate-limit · durcissement exposition | T4 ✅ | ✅ **fait** : mode public **enforced** (cloud→403) · rate-limit durci (purge IP) · CSRF · CSP `'self'` · upload double-cap (413+422) ; *multi-worker = limite documentée (Space mono-worker)* |
| **S6** surfaces UI | segmentation-UI · importeurs-UI | **T5** / **T7** | ⛔ bloqué (attend l'axe moteur) |
| **Rapport autonome interactif** | HTML déterministe sans backend (artefact ≈ T1) | T1 ✅ | ✅ |

> **Alias historiques** (commits / anciens docs) : `TU1=S1` · `TU2=S2` · `TU3=S3` ·
> `TU4=S4` · `TU6=S5` · `TU5=T7` · `TU7=T5`. Le **statut fait foi ici** ;
> [`PLAN_SPACE_INTERACTIF.md`](PLAN_SPACE_INTERACTIF.md) = **spec UX**, sans roadmap.

**Règle anti-dérive (corollaire de « pas de consommateur = supprimé »)** : on ne
crée **pas** d'API/symbole public avant que **son consommateur de la même
sous-tranche** existe. Une API posée « en prévision » d'une sous-tranche ultérieure
est du spéculatif → élaguée à la revue (précédents : `blocked_cloud_kinds`,
`CLOUD_KINDS` dupliqué, retirés au commit `5c17cf2`).

### Rituel de réconciliation (NON négociable — c'est ce qui rend la redondance utile)

À chaque tranche, l'agent de construction :
1. **lit les deux** — ce plan (tranche + roll-up) **et** la `DoD vivante` de chaque couche touchée ;
2. **coche uniquement ce qu'un *gate nommé* prouve** (test/commande/grep) — jamais « je l'affirme » ;
3. **si pas coché → écrit pourquoi** (différé-par-design vs réserve-ouverte vs bloqué) ;
4. **si le plan et une DoD de couche divergent → arbitre** : corrige l'un, **ou** justifie l'écart dans le **journal de décisions** (§10) ;
5. **met à jour les deux dans le MÊME commit que le code** (règle d'or anti-dérive : les docs de Picarones mentaient parce qu'ils étaient mis à jour à part, ou jamais) ;
6. **n'ajoute les cases de *surface*** (quelle métrique/route exactement) **qu'au démarrage de la tranche** — pas toutes d'avance (l'enveloppe est détaillée maintenant, la surface est périssable).

---

## 0. Principes directeurs → mécanismes concrets

Les quatre exigences du projet ne sont pas des slogans : chacune est portée par un
mécanisme vérifiable, et **c'est elle qui justifie la découpe en tranches**.

| Principe | Mécanisme qui le garantit |
|---|---|
| **Simplicité** | 1 contrat de module (pas 4 registres) · 1 format de sortie `RunResult` (pas le double `BenchmarkResult`) · 1 signature de section · 1 pile HTTP. Chaque tranche **ajoute un seul concept**. |
| **Maintenabilité** | Budgets `<400 LOC` + `test_file_budgets` · garde-fous d'archi **dès la 1ʳᵉ tranche** · **zéro shim** · « pas de consommateur = supprimé » · golden **octet-stable** (déterminisme prouvé, pas espéré). |
| **Intelligence conceptuelle** | L'**enveloppe est dimensionnée plein-scope une fois** (axe 1, §1) : `RunResult` porte structure/NER/taxonomy **dès sa conception**, le registre est **générique sur `input_types`**. On coule des fondations pour 3 étages, on meuble un étage à la fois. |
| **Extensibilité (tranche→tranche & futur)** | **Un seul point d'extension** : le `Module` Protocol + entry-points `xerocr.modules`. Chaque tranche ne fait qu'**ajouter** (un module, une métrique, une section) sur des contrats **stables** → elle ne modifie jamais l'enveloppe précédente. **Inner→outer** : chaque tranche ne dépend que de couches finies. |

---

## 1. Invariants d'enveloppe — figés UNE fois, dès la tranche 1

Cœur de l'« intelligence conceptuelle » : ces contrats sont conçus **plein-scope
maintenant**, même remplis minimalement, pour que **rien d'aval ne force jamais leur
réécriture**. Une tranche ultérieure les **remplit** ; si elle doit les **modifier**,
c'est le signal qu'ils étaient mal dimensionnés → on s'arrête et on reconçoit.

| Pivot | Conçu pour (plein-scope) | Rempli en T1 (minimal) | Rend extensible |
|---|---|---|---|
| **`RunResult`** (`evaluation/result.py`) | CER/WER **+** taxonomy/NER/calibration/**structure** + par-doc + `schema_version` | 1 seul CER | toute métrique future = champ déjà prévu |
| **Registre type-driven** | sélection **100 % par `input_types`** | 1 métrique `(RAW_TEXT,RAW_TEXT)` | `(LAYOUT,LAYOUT)`, `(ENTITIES,…)` sans toucher le registre |
| **`Module` Protocol** (couche 4) | `name` · **`version`** · `input_types`/`output_types` · `execute(inputs,params,context,control)` | `precomputed` | tout module OCR/HTR/VLM/segmenteur/post-correcteur, **first-party ou tiers** |
| **`Protocol Section`** (`reports`) | 1 signature `render(RunResult, ctx) → Html\|None` + `requires` déclarés | 1 section overview/CER | toute section future, **sans data-layer** |
| **`ArtifactType.LAYOUT` + `region_id`** | réservés en couche 1 (déjà présents) | non utilisés | la tranche structure (fan-out région) **sans migration** |
| **Registre de modules + factory** (`app/modules/`) | résolution `name→Module` + **découverte entry-points** prête | 1 module en dur | plugins tiers (T6) |
| **`RunManifest`** (provenance câblée) | code_version + deps + binaires + hash params | rempli par l'executor dès T1 | reproductibilité de tout run futur |

---

## 2. Séquencement des tranches

```
T0  Fondations (domain + formats)                       [horizontal — vert, voir §9]
      │
T1  SQUELETTE AMBULANT  ── prouve l'enveloppe entière ──▶  xerocr demo
      │   3·4·5·6·7·8 · 1 CER · precomputed
T2  AXE TEXTE + 1er moteur réel ───────────────────────▶  xerocr run / compare
      │   tesseract · WER/MER · stats scipy · cross-engine · sécurité · repro
T3  OCR + LLM (post-correction) ───────────────────────▶  pipeline 2 étapes
      │   openai + ollama · 2e famille de module
T4  SOCLE WEB (couche 8 : create_app · security/ · vitrine READ-ONLY) ─▶ xerocr serve
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
T5  STRUCTURE (segmentation / layout)  ★ ──────────────▶ métriques structurelles
      │   CanonicalLayout · fan-out région · segmenteur de référence   ──⟸ débloque S6-seg
T6  EXTENSIBILITÉ TIERCE  ★ ──────────────────────────▶  charger un module hors-arbre
T7  SURFACES INTERNES ──────────────────────────────────▶ importeurs cœur ──⟸ débloque S6-imp
          longitudinal · philologie · taxo · économie · métriques

   ════════════ AXE SPACE  S#  (app web · couche 8+déploiement · CONSOMME le moteur) ════════════
S1 coquille au design ✅           S2 lanceur (run/SSE/Moteurs/upload/gardes) 🔨  ⟸ T2,T3,T4
S3 persistance ⟸ T4               S4 vues rapport au design ⟸ couche 7
S5 sécurité publique ⟸ T4         S6 surfaces UI (segmentation/importeurs) ⟸ T5 / T7
```

Règle : chaque tranche est **fine mais de pleine profondeur** (tourne de bout en bout).
On n'ouvre l'axe **structure** (T5) qu'après avoir prouvé l'axe **texte** (T1-T3).
Aligné sur `MIGRATION_COUCHE_3.md` §15 (étend sa vue eval-centrée à serve / OCR+LLM /
importeurs / extensibilité / infra).

---

## 3. Détail par tranche

### T1 — Squelette ambulant

| | |
|---|---|
| **Objectif** | Prouver que **toute l'enveloppe s'emboîte** de bout en bout avec **une seule métrique scalaire**. Fin **et** de pleine profondeur. |
| **Traverse** | 3 (registre + `RunResult` + runner 1 métrique + `safe_*`) · 4 (`Module` Protocol + executor minimal) · 5 (`precomputed`) · 6 (orchestrateur minimal + `RunSpec` minimal + registre 1 module + provenance) · 7 (`Protocol Section` + `html` + 1 section) · 8 (CLI `demo`) |
| **Enveloppe figée** | les 7 pivots du §1 |
| **Surface minimale** | 1 module `precomputed` · 1 métrique `CER (RAW_TEXT,RAW_TEXT)` · 1 section overview/engines |
| **Élimine d'emblée** | double format (1 seul `RunResult`) · 4 registres→1 · narratif (jamais créé) · effets de bord d'import · data-layer |
| **Validation** | `xerocr demo --output r.html` → **HTML déterministe** · golden octet-stable · provenance dans `RunManifest` · import sans effet de bord |
| **Diffère** | tout moteur réel · stats · `CanonicalLayout` · web · multi-étapes |

### T2 — Axe texte + premier moteur réel

| | |
|---|---|
| **Objectif** | Un **vrai moteur** + la profondeur métrique texte + les stats + `compare`. **Tue la conversion double-format.** |
| **Traverse** | 3 (WER/MER + noyau texte **clés stables** + `profiles` + **scipy** + `cross_engine`→`RunResult`) · 5 (`tesseract`+`confidences`, utils racine) · 6 (orchestrateur réel + loader YAML + **sécurité chemins** + capture deps/binaires) · 7 (sections engines/cross + `compare.py`) · 8 (`run` + `compare`) |
| **Élimine** | conversion `RunResult→BenchmarkResult` supprimée · sécurité chemins fidèle et testée d'abord · provenance câblée · `_retry` unifié (bug jitter corrigé) |
| **Validation** | parité métriques vs `jiwer` · **run rejouable depuis le `RunManifest` seul** · entrées dégénérées→`None` · golden `RunResult` |
| **Diffère** | LLM · web · structure · importeurs réseau |

### T3 — OCR + LLM (post-correction)

| | |
|---|---|
| **Objectif** | Prouver les **pipelines multi-étapes** + une **2ᵉ famille de module** sur le même `Protocol`. |
| **Traverse** | 5 (`llm/base` splitté + `openai` + `ollama`) · 4 (binding `OCR→LLM`, executor multi-step) · 6 (`make_ocr_llm_pipeline_spec` mode `text_only`) · 8 (`run` pipeline) |
| **Élimine** | triple alias `PipelineMode`→1 · `llm/base` >400 splitté · `tokens_used` peuplé ou supprimé · annulation `control` câblée (ollama = référence) |
| **Validation** | `tesseract → llm text_only` produit du `CORRECTED_TEXT` non vide (bug historique Picarones) · le 2ᵉ module passe le **même** contrat sans cas particulier |
| **Diffère** | `zero_shot`/VLM (**0 consommateur** → non porté) |

### T4 — socle web (couche 8, **read-only**)

| | |
|---|---|
| **Objectif** | Poser l'**enveloppe de transport** et **servir** les rapports : la base sur laquelle l'axe **Space `S#`** se construit. |
| **Traverse** | 8 (`create_app()` factory · routers `home`/`reports` · package `security/` : CSP/rate-limit/en-têtes · chemins validés) |
| **Élimine** | effets de bord d'import (factory) · sécurité éclatée 7 modules→1 package |
| **Validation** | factory (instances neuves) · CSP stricte · `..`/symlink→404 · `serve` fumé via uvicorn · Docker/Space déployable **sans clé** |
| **Diffère** | tout l'**interactif** → axe **Space `S#`** (lanceur, jobs, SSE, upload, mode public) |

### Axe Space `S#` (app web interactive · couche 8 + déploiement) — détail

> Le Space **consomme** le moteur (`⟸`). Statut dans le tableau « Les deux axes »
> du roll-up ; `PLAN_SPACE_INTERACTIF.md` = spec UX des écrans.

| `S#` | Livre | ⟸ | Élimine / Valide | ex-TU |
|---|---|---|---|---|
| **S1** | coquille au design (Jinja + CSS, polices self-host, nav, FR/EN) | T4 | SPA lourde → rendu serveur ; CDN → self-host | TU1 |
| **S2** ✅ | lanceur : `JobRunner`+`JobStore` (annulation), `/api/engines` + page `/engines`, upload ZIP durci, gardes HTTP, SSE+`Last-Event-ID`, page JS `/benchmark` + **UI upload/sélection moteur** | T2,T3,T4 | 2 JobStore→1 (SSE réabsorbé) · annulation réelle · CSRF/mode public/zip-bomb **verts d'abord** ; run moteur réel = test `live` | TU2 |
| **S3** ✅ | persistance : `ResultPublisher` (couche 5) pousse le `RunResult` JSON vers un dépôt GitHub (API *contents*, `urllib`) après un run réussi — **opt-in via secrets** (`XEROCR_PUBLISH_REPO`/`_TOKEN`), **best-effort** (un échec ne fait pas échouer le run), jeton jamais journalisé ; `published_url` remonte sur le `Job`. Push réel = test `live` | T4 | disque HF éphémère → push durable ; la vitrine **rend** le JSON (pas besoin de pousser le HTML) | TU3 |
| **S4** ✅ | vues rapport au design : **S4.a** chrome rapport (gris chaud · en-tête pilule · cartes `sec` · tables tabulaires → autonome + octet-stable) + overview restylé ✅ · **S4.b.1a** polices du design **incorporées en data-URI** (Fluxisch Else + OCR-A, `reports/_style`) ✅ · **S4.b.1b** overview enrichi (**readouts** de portée + **data-bars** relatifs à la colonne) ✅ · **S4.b.2** section **par-document** (surface `RunResult.documents` — déjà calculé, jamais rendu — doc×pipeline groupé + data-bars) ✅ · **S4.b.3** **par-moteur** (classement trié + dispersion par-doc) ✅ · **S4.b.4** **crosses** au design (clé éclatée Vue/Métrique + verdict factuel) ✅ ; **synthesis** différé T7 | couche 7 | data-layer → lit `RunResult` direct | TU4 |
| **S5** | sécurité publique : mode public · quotas · rate-limit · durcissement | T4 | exposition non bornée | TU6 |
| **S6** | surfaces UI : segmentation-UI ⟸ **T5** · importeurs-UI ⟸ **T7** | T5 / T7 | — | TU7 / TU5 |

### T5 — Structure (segmentation / layout) ★ ambition nouvelle

| | |
|---|---|
| **Objectif** | **Matérialiser** ce que l'enveloppe réservait depuis T1. La **preuve que le dimensionnement précoce a payé** — zéro réécriture des couches 1-4. |
| **Traverse** | 1 (`CanonicalLayout` + parties en `domain`) · 2 (mappers `alto/page→layout`) · 3 (projecteur `layout→text` + **shapely** confiné + `region_detection`/`line_detection`/`reading_order`/`geometry_coverage`) · 4 (**fan-out** : segmentation → reconnaissance par région → réassemblage + routage par type de bloc) |
| **Ambition** | `segmentation (IMAGE→LAYOUT) → reconnaissance par région → assemblage (LAYOUT→ALTO)` + segmenteur de référence (starter pack) |
| **Validation** | `region_id` exercé · `RunResult` accueille une métrique `(LAYOUT,LAYOUT)` **sans modif de contrat** · golden **ALTO+PAGE** · round-trip fidélité |
| **Test conceptuel** | si T5 force à changer `RunResult`/registre/`Module`, le dimensionnement de T1 était faux. Attendu : elle ne fait qu'**ajouter**. |
| **Guide de portage** | `xerocr/pipeline/ANALYSE_T5_SEGMENTATION.md` (analyse durable Picarones + design cible PROVISOIRE + squelette + risques) |

### T6 — Extensibilité tierce ★ ambition nouvelle

| | |
|---|---|
| **Objectif** | **Ouvrir** le point d'extension unique : charger un **module hors-arbre** sans forker. |
| **Traverse** | 6 (`app/modules/` : découverte **entry-points `xerocr.modules`** + `register()` local + capture de **version** plugin → `RunManifest`) · 8 (mode public **désactive** la découverte : in-process = sécurité) |
| **Périmètre STRICT** | seules les **briques de pipeline** sont pluggables. Métriques/importeurs/sections/projecteurs/stats restent **first-party**. |
| **Validation** | 1 **plugin de référence** out-of-tree chargé/exécuté via le **même** `Protocol` · sa `version` remonte au `RunManifest` · en mode public, découverte **fail-closed** |

### T7+ — Surfaces incrémentales (1 concept par tranche, avec consommateur réel)

| Tranche | Ajout | Élimine au passage |
|---|---|---|
| **Importeurs** (IIIF→Gallica→eScriptorium→HTR-United→HF, 1/tranche) | sortie **unique `Corpus`** ; orchestration disque en `app` | bugs latents `Corpus(source=)`/`selected_indices+1` corrigés + test `live` · `_fallback_log` supprimé · **données démo en dur→`data/`** · dict-manifestes→`Corpus` |
| **Longitudinal** | store **tidy** en `adapters/storage` + section history | `history` SQLite changé de couche |
| **Philologie / Taxonomie / Économie / Image** | 1 métrique + 1 section par tranche | métriques mortes/doublons non portées · clés stables |
| **Observabilité / RGPD / Docker / Release** | `/metrics` opt-in · purge RGPD · Dockerfile · CI release | scripts sprint morts · `docs/archive` non migrés |

---

## 4. Matrice — chaque problème Picarones → la tranche qui l'élimine

| # | Problème Picarones | Éliminé en | Comment |
|---|---|---|---|
| F1 | Double format `BenchmarkResult↔RunResult` | **T1**→**T2** | 1 seul `RunResult` dès le départ ; conversion supprimée |
| F2 | Deux chemins de rapport + data-layer | **T1** | `Protocol Section` lit `RunResult` direct |
| F3 | 4 registres parallèles | **T1** | 1 registre type-driven |
| F4 | Code mort (`cache.py`,`yaml_io.py`,½ partial_store) | **jamais porté** | « pas de conso = supprimé » |
| F5 | 424 annotations de sprint | **transverse** | « garder le pourquoi, jeter la datation » |
| F6 | Fichiers >400 LOC | **transverse** | `test_file_budgets` |
| F7 | Moteur narratif | **jamais porté** | supprimé (D2) |
| F8 | 2 JobStore (SSE perdu) | **S2** | 1 store + SSE réabsorbé avant suppression legacy |
| F9 | Bugs latents masqués par mocks | **T7 importeurs** | corrigés + test `live`/`network` |
| F10 | Provenance dormante | **T1** | câblée dans l'executor |
| F11 | Annulation/deadline non câblées | **T3**→**S2** | `RunControl`/`Deadline` réels de bout en bout |
| F12 | Effets de bord d'import | **T1/T4** | `__init__` minces · `create_app()` factory |
| F13 | Données fabriquées en dur (~220 LOC) | **T7 importeurs** | `data/*.yaml` + `is_demo` |
| F14 | Sécurité éclatée (7 modules) | **T4** | 1 package `security/` |

→ 100 % des problèmes audités sont adressés, chacun à une tranche nommée.

## 5. Matrice — chaque ambition XerOCR → la tranche qui la matérialise

| Ambition (`CLAUDE.md`) | Enveloppe dès | Matérialisée en |
|---|---|---|
| Banc déterministe/reproductible + rapport factuel | T1 | T1 → T2 |
| **Extensibilité par modules tiers** | T1 (Module+registre) | **T6** (entry-points + plugin de référence) |
| **Segmentation/layout + fan-out région** | T1 (`LAYOUT`+`region_id`) | **T5** |
| Starter pack (precomputed/tesseract/openai/ollama/segmenteur) | T1 | T1→T2→T3→T5 |
| Sécurité in-process (mode public) | T1 | S5 + T6 |
| Anti-hallucination / what-if = sélection jamais re-mesure | T1 (`RunResult` par-doc) | tranche tardive (§8) |

---

## 6. Comment chaque tranche facilite la suivante

- **T1 fixe l'enveloppe** → T2…T7 n'**ajoutent** que de la surface sur des contrats stables : aucune ne réécrit une couche déjà faite.
- **Inner→outer** → quand on écrit T_n, ses dépendances (couches plus internes) sont finies et testées : pas de blocage « vers l'avant ».
- **Registre générique sur `input_types`** → ajouter une métrique = une fonction + une fiche ; le registre ne change pas. Idem `Protocol Section`.
- **`Module` Protocol unique** → ajouter un moteur (T2/T3/T5) **ou** un plugin tiers (T6) = la **même** opération. T6 ne fait qu'**exposer** la prise que T1 a conçue.
- **`RunResult` plein-scope** → une métrique structurelle (T5) atterrit dans un champ **déjà prévu** ; le rapport la lit sans data-layer.

---

## 7. Garde-fous transverses (actifs à chaque tranche)

1. **Tests d'archi dès le 1ᵉʳ commit de code de la tranche** : `layer_dependencies`, `no_legacy_imports`, **`no_side_effect_imports`**, **`file_budgets`**, `no_broad_except`, `single_version_source` (+ `no-orphan métrique↔section` dès T1).
2. **Budgets `<400 LOC`** ou entrée justifiée.
3. **Zéro shim, rupture nette** : un seul chemin, jamais d'ancien gardé « le temps de migrer ».
4. **« Pas de consommateur = supprimé »** : aucune surface spéculative.
5. **Golden déterministe refait** (jamais hérité de Picarones — incompatibilité numérique assumée, `MIGRATION_COUCHE_2.md` MIG-2).
6. **Une tranche = livrable end-to-end vert** (mypy + ruff + pytest) avant la suivante.

---

## 8. Points de décision ouverts (à trancher au build)

| Décision | Tranche | Options |
|---|---|---|
| Mécanisme what-if (rapport filtrable) | tardive | (a) runner pré-calcule → rapport sélectionne *(recommandé)* ; (b) ré-agrégation client |
| `control`/deadline : honorer vs best-effort | T3/T4, **par adapter** | trancher cas par cas, ne pas traîner un param non câblé |
| Placement `corpus_service` (ZIP+appariement) | T7 importeurs | `app` vs `adapters/corpus` |
| Forme exacte de `CanonicalLayout` | T5 | à confirmer **avec son 1ᵉʳ consommateur**, pas avant |
| Pile HTTP unique (`httpx`) vs dual SDK/REST | T2/T7 | `httpx` pour auth simple ; SDK gardé pour Google/Azure |

---

## 9. État vérifié de T0 (fondations) — vert, mais pas « clos »

Mesuré le 2026-05-31 sur la branche de travail :

| Gate | Résultat |
|---|---|
| `pytest tests/` | **158 passed**, **95,14 %** coverage |
| `mypy --strict -p xerocr.domain` / `mypy -p xerocr.formats` | **Success, 0 issue** |
| `ruff check xerocr/ tests/` | **All checks passed** |
| DoD couche 1 — symboles interdits | **absents** (`PicaronesError`/`BaseModule`/`Fact`/`LEGACY_VALUE_ALIASES`/`pipeline_names`) |
| `ArtifactType.LAYOUT` + `Artifact.region_id` | présents (`xerocr/domain/artifacts.py`) |
| Tests sécurité XML + ordre de normalisation | présents (`tests/formats/test_xml.py`, `…/text/test_normalization_edges.py`) |
| Marqueurs d'inachevé (`TODO`/`NotImplementedError`/`...`) | **aucun** dans `domain`+`formats` |

**Réserves à lever avant de déclarer T0 « clos » (≠ différés par design) :**

1. **2 garde-fous d'archi manquants** : `tests/architecture/` ne contient que 4 tests ;
   **`test_no_side_effect_imports`** (exigé `MIGRATION_COUCHE_1.md §7`) et
   **`test_file_budgets`** (`CLAUDE.md §5`) sont **absents**. L'import est propre
   aujourd'hui, mais rien n'empêche une régression.
2. **`CLAUDE.md §0` périmé** : annonce « dépôt vierge… aucune couche implémentée »,
   branche obsolète. À corriger (induit en erreur une session fraîche).
3. **Types domain sans consommateur** (`EvaluationSpec`/`ProjectionSpec`/`evaluation.py`) :
   gardés délibérément comme vocabulaire déclaratif, mais à **assumer consciemment** au
   regard du garde-fou « pas de consommateur = supprimé ».

**Différés par design (NON des manques)** : backlog domain (`RunSpec`/`ProjectionReport`/
`ConfidenceToken`), `CanonicalLayout`, l'assembleur — reportés à leur tranche
(anti-spéculatif).

---

## Cibles de distribution (calcul vs vitrine)

> **Principe :** séparer le **calcul** (produire des résultats — exige moteurs/clés) de la
> **vitrine** (montrer des résultats — n'exige rien). L'archi (déterminisme + `RunManifest` +
> adapter `precomputed` + rapport HTML autonome) est faite pour ce découplage.

| | **Calcul** | **Vitrine** |
|---|---|---|
| Où | en **local** (`serve`/CLI) : tes clés, tes corpus, privé | **hébergée**, partageable |
| Clés | oui (les tiennes, sur ta machine) | **aucune** déployée |
| Coût / abus | tu ne paies que tes runs | nul (rien à calculer) |
| Quoi | moteurs OCR/LLM | **rapport HTML autonome, interactif côté navigateur** (repli/tri/filtre/comparaison de runs **déjà calculés** ; jamais de re-mesure) |

**Canaux, par engagement croissant — le Space n'est PAS optionnel :**

1. **Rapport autonome interactif** — livrable **≈ T1**. HTML déterministe, sans backend, sans clé, sans CDN ; interactif dans le navigateur (sélection/exploration, pas de recalcul). **Premier artefact partageable**, pas un substitut du Space.
2. **Space hébergé « vitrine » (mode public)** — **cible engagée, axe Space `S#`** (sur le socle T4). Sert tes runs pré-calculés via l'app complète ; allowlist **fail-closed** (moteurs à clé bloqués) ; **zéro secret déployé**. La démo publique.
3. **BYO-key par *duplication*** — **quasi-gratuit si (2) est bâti propre** (config-par-secrets, boot-sans-secret, fail-closed) : activer = surtout **documenter** le flux *Duplicate this Space* (chaque user met SA clé dans SA copie). La **custodie de secrets reste hors de ton assiette**. Coûts : friction (compte HF + hardware) et forks qui vieillissent (pas de push de fix ; `RunManifest` rend la divergence détectable).
4. **Service partagé BYO-key** (une boîte, clés saisies chez toi) — **non retenu par défaut** : custodie de secrets + limites anti-abus + hygiène **testée** (DoD couche 8). À n'ouvrir que sur besoin explicite.

**Écarté :** desktop bundlé PyInstaller (D-006) — « install facile » = vitrine + `pipx`/`serve`.

**Conséquences de conception (couche 8) :** la vitrine est **duplicable par construction** dès
sa v1 ; et comme **ton code tourne avec la clé d'autrui en mode dupliqué**, l'hygiène des clés
(mémoire-seule, jamais journalisée/persistée/rendue) est un invariant **testé**, pas une intention.

---

## 10. Journal de décisions (ADR-lite, append-only)

> Toute décision/arbitrage qui **confirme, corrige ou contredit** un verdict
> PROVISOIRE d'un `COUCHE` doc, ou qui ajoute un choix transverse, est tracée ici.
> « Expliquer tous les choix faits » — garder le *pourquoi*, dater l'entrée.

| ID | Date | Tranche | Question / arbitrage | Verdict | Pourquoi | Remplace quel PROVISOIRE |
|---|---|---|---|---|---|---|
| D-001 | 2026-05-31 | T0 | `model_rebuild()` au niveau module est-il un effet de bord interdit ? | **Allowlisté** dans `test_no_side_effect_imports` | Idiome Pydantic v2 pur/idempotent/requis pour modèles récursifs (régions imbriquées) ; ≠ `register_default_metrics()` | — (découvert en calibrant le gate) |
| D-002 | 2026-05-31 | T0 | 2 garde-fous d'archi manquants | **Ajoutés** : `no_side_effect_imports` + `file_budgets` | Exigés par `MIGRATION_COUCHE_1 §7` + `CLAUDE.md §5` ; étaient absents → régression possible | comble la DoD couche 1 |
| D-003 | 2026-05-31 | transverse | Un agent affirmait « 27 violations d'archi en `interfaces` » | **Réfuté** : ce sont des imports légaux (couche plus interne) | `test_layer_dependencies` l.258 « peut importer plus interne » ; CI verte. C'est une **convention** (le run passe par `app`), pas une violation dure | crée la convention L7 (plan §8) |
| D-004 | 2026-05-31 | méthode | Où vit la DoD vivante ? | **Dans chaque `COUCHE` doc** + plan = roll-up/orchestration/journal | Redondance plan↔couche = **détection d'erreur** (réconciliation forcée), pas duplication ; les deux sont complémentaires | — |
| D-005 | 2026-05-31 | méthode | Granularité des cases par tranche | **Enveloppe + garde-fous + validation** | Signal porteur sans bruit (≠ case par fichier) | — |
| D-006 | 2026-05-31 | distribution | Comment partager / qui peut l'utiliser ? | **Vitrine hébergée non-optionnelle (T4), duplicable par construction** ; desktop écarté | Découpler calcul (local, tes clés) / vitrine (sans clé) ; BYO-key par *duplication* HF = doc, pas un chantier (custodie de secrets hors de ton assiette) ; rapport autonome **interactif** = artefact T1 | crée §Cibles de distribution |
| D-007 | 2026-05-31 | T1 | Outillage métrique & CLI (deps minimales) | **CER = impl maison déterministe** (jiwer = oracle de parité à T2) ; **CLI = argparse** (stdlib) | `pyproject` n'a ni `jiwer` ni `click` ; squelette **sans dépendance ajoutée** + contrôle du déterminisme ; cadre le T2 « parité vs jiwer » | — |
| D-008 | 2026-05-31 | T1 | `RunControl` : `raise_if_cancelled` à garder ou retirer ? | **Conservé** (et devient le mécanisme d'annulation coopératif) ; `register_cancel_handle` **omis** (0 conso) | L'analyse couche 4 disait « retirer, 0 conso » — **corrigé** : en T1, executor + `precomputed` l'appellent (tests verts), donc il A un consommateur. Le handle SDK, lui, reste omis jusqu'à l'adapter LLM (T3/T4) | corrige verdict ANALYSE_COUCHE_4 (`run_control`) |
| D-009 | 2026-05-31 | T1 (couche 3) | Réserve T0 : `EvaluationSpec`/`ProjectionSpec` sans consommateur | `MetricSpec`/`EvaluationView`/`EvaluationSpec` **confirmés** (registre + runner les consomment) ; `ProjectionSpec` **différé** (T2, projections) | T1 leur donne enfin un consommateur → lève la tension « pas de conso = supprimé » pour les 3 ; `ProjectionSpec` attend sa tranche | lève partiellement la réserve couche 1 §8 |
| D-010 | 2026-05-31 | T1 (couche 6) | `RunSpec` : reprendre le `StepSpec` de l'héritage ? | **Non** — `RunSpec` compose `PipelineSpec`/`PipelineStep` (domain) directement ; **pas de `StepSpec`** | Un `StepSpec` distinct = **2ᵉ représentation de pipeline** (la dette qu'on tue) ; `PipelineStep` déclaratif suffit. La factory résout `<kind>:<label>` via un **builder enregistré** (pas d'import de chemin pointé) | raffine le backlog CLAUDE (`RunSpec (+StepSpec)`) |
| D-011 | 2026-05-31 | T1 (clôture) | Golden du rapport : snapshot stocké ou déterminisme par construction ? | **Déterminisme par construction** : la section overview ne rend **ni timestamp ni chemin ni version** → HTML naturellement octet-stable | Un snapshot HTML stocké casse à chaque retouche CSS (fragile) ; « 2 runs == identiques » tient l'invariant §12 sans ce fardeau | clôt T1 (`xerocr demo` octet-stable) |
| D-012 | 2026-05-31 | revue T1 | Frontière de déterminisme : timestamps wall-clock (provenance, manifest, `run_id` par défaut) | **Métadonnée EXCLUE de l'identité** ; jamais rendue dans `RunResult`/HTML (vérifié : demo octet-stable) | §12 = « hash identique » (content_hash déterministe) ; `ProvenanceRecord.is_compatible_with` exclut déjà le timestamp ; cohérent avec `RunManifest` | guide le cache/store T2+ : clé = content_hash, **pas** `model_dump_json` |
| D-013 | 2026-05-31 | revue T1 | Revue complète (3 angles : ligne-à-ligne, inter-fichiers/déterminisme, qualité/altitude) | **0 bug T1** ; robustesse différée | Code déjà passé ruff/mypy/pytest. Sans conso T1 (pas de spéculation) : validation module↔step + `inputs_from` au **loader YAML (T2)** ; précision `run_id` au **store (T4)** ; I/O texte dédupliqué si chaud. **+ corrige** : `make type` ne couvrait pas les couches T1 → `mypy -p xerocr` | trace l'audit + ses suites |
| D-014 | 2026-05-31 | T3 | `register_cancel_handle` : distinguer une **annulation** d'une vraie panne réseau ? | **Sonder `is_cancelled` après l'échec** (`_fail_or_cancel`) ; mécanisme thread-safe (`Lock`) livré **avec son 1ᵉʳ consommateur** (`ollama`) → clôt le différé D-008 | L'implémentation source **devinait par le message** d'exception (fragile, dette D-A) ; sonder l'état est fiable. Le sondage coopératif (`raise_if_cancelled`) reste la **garantie** ; le handle est best-effort (un `cancel_event` partagé `set()` hors `trigger_cancel` ne déclenche pas les handles — limite assumée, documentée) | clôt D-008 (handle différé) + dette D-A (couche 5) |
| D-015 | 2026-05-31 | réconciliation T3 | Le roll-up (index) marquait encore **T1** pour les couches 3-8 alors que T2/T3 avaient shippé | **Index resynchronisé** sur les DoD par couche (autorité) : 3→T2, 4→T3, 5→T3 complet, 6→T3, 7→T2, 8→T2 ; lignes tranches T2/T3 ajoutées | Le rituel de réconciliation a **détecté une dérive réelle** (DoD par couche à jour, index en retard) — précisément ce que la redondance D-004 doit attraper ; corrigé dans ce commit | applique le rituel §Réconciliation |
| D-016 | 2026-05-31 | audit T2/T3 | Audit impitoyable de T2/T3 : 1 bug HIGH + 5 MEDIUM. Que corriger, et comment trancher les 2 choix de méthode ? | **HIGH** : contamination inter-pipelines (workspace partagé) → **isolation par sous-dossier**. **MEDIUM** : agrégat macro→**micro** (Σerr/Σpoids, macro reconstructible) ; `_MIN_SUPPORT` 2→**6** (plancher de puissance) + `ValueError→None` ; **`module_versions`** au manifeste (R-2) ; robustesse (GT `must_exist`, `OSError→EvaluationError`) ; parité MER **verrouillée** sur cas ambigu + honnêteté du docstring | Le bug HIGH brisait l'usage cœur (comparer 2 pipelines). Micro = la métrique conventionnelle, comparable à `jiwer`-corpus, et **macro reste dérivable** du détail par-doc → on garde les deux sans gonfler l'enveloppe. Plancher 6 : sous lui un Wilcoxon ne **peut** pas être significatif → `None` plutôt qu'un faux verdict. Parité MER exacte avec jiwer (tie-break d'alignement) = **non poursuivie** (coût/risque) : comportement déterministe pinné, divergence documentée | clôt l'audit ; `safe_mean` supprimé (0 conso) ; binaire tesseract→`system_binaries_lock` reste différé (live) |

| D-017 | 2026-05-31 | audit T2/T3 (LOW) | Balayage des 6 findings LOW + revue du balayage lui-même | CLI : erreurs métier/E-S → message + code 1 (plus de trace nue) · `_candidate_for` : **précédence explicite** (corrigé > brut), plus l'ordre alphabétique d'enum · `compare` : libellé Δ nommant les taux d'erreur (CER/WER/MER) · stem de fichier **injectif** via encodage URL · `expanduser` mort retiré (sécurité) · `--json` non-octet-stable = **laissé tel quel** (correct par D-012) | La **revue d'après** a rattrapé un **vrai bug que j'avais introduit** : l'échappement maison du stem (`_→__` puis `/→_`) collisionnait `a/_b` et `a_/b` → remplacé par `quote()` réversible (test de non-collision ajouté). Confirme que « corriger puis re-réviser » attrape ce qu'une seule passe rate | clôt le balayage LOW ; valide le rituel de revue |
| D-018 | 2026-06-01 | S4.b (pré-requis design) | `design/` empilait **3 générations contradictoires** (① polices CDN Bricolage/IBM Plex/Apfel · ② branding « Picarones » · ③ spec XerOCR) ; les `screenshots` étaient figés en ①+② (**sans la trame de points**) et les CSS se contredisaient (`--display` = Bricolage *vs* OCR-A selon le fichier) | **Consolidé en UNE source = ③** : **Fluxisch Else** (titres) + **OCR-A** (corps/données) **self-hosted**, `@font-face` + variables `--display/--sans/--mono/--serif` dans **`tokens.css` seul** (`picarones.css` hérite), branding **XerOCR**, **trame Xerox** confirmée. **Supprimé** : 5 mockups CDN, `design-canvas.jsx` (canvas orphelin), 5 screenshots périmés. **Ajouté** : `design/render/` (harnais offline reproductible, zéro réseau au rendu) → `screenshots/report-{overview,by-engine,by-document,crosses}.png` régénérés | Le garde-fou S4.b « comparer au `design/screenshots` » reposait sur une **référence fausse** (polices CDN, Picarones, sans trame). Source unique ⇒ changer la typo = **1 endroit** (trivial) et rendu **déterministe/offline**. Confirme la résolution typo de `design/README` | prépare la **décision police du rapport autonome** (S4.b) : **incorporer les woff2 en data-URI** (identité Fluxisch Else + OCR-A **et** autonomie — option (a) du brief) |
| D-019 | 2026-06-01 | S4.b.1a | Police du rapport autonome (décision **préparée par D-018**) : **système**, **`/static`**, ou **incorporée** ? | **Option (a) — woff2 incorporés en data-URI** : `reports/_assets/*.woff2` (couche 7, **sans dépendre de la couche 8**) ; `_style.font_face_css()` les lit → base64 → `@font-face data:` préfixés au CSS (Fluxisch Else Regular+Bold + OCR-A, 166 Ko). Titres **Fluxisch Else**, corps + données **OCR-A** | **Système** = identité partielle (perd les polices du design) ; **`/static`** = perd l'autonomie du *standalone* (le rapport doit s'ouvrir hors serveur). data-URI garde **identité + autonomie + octet-stabilité** (base64 d'octets figés = déterministe ; rapport 4,4→227 Ko, prix assumé) | a révélé un **test fragile** : `assert "WER" not in html` collisionnait le base64 → durci en `"<p>WER</p>"` (markup réel). reste **S4.b.1b** readouts/data-bars + overview riche |
| D-020 | 2026-06-02 | corpus réel (BNL) | Brancher un **vrai** corpus patrimonial (la démo n'avait que 3 docs synthétiques) + autant de moteurs accessibles que possible ? | **Mini-GT BNL** (presse luxembourgeoise XIXᵉ, **multilingue** allemand Fraktur + français, données ouvertes) en **fixture déterministe** `tests/fixtures/reference_corpus/bnl_mini/` : **30 docs**, GT extraite des ALTO v4 BNL + sorties OCR **figées** rejouées via `precomputed` → **CI-safe sans moteur**. **5 moteurs** : 4 Tesseract (`frk` Fraktur legacy · `deu` allemand · `fra` français · `deu_latf` Fraktur LSTM best) **+ `easyocr`** (deep-learning, autre architecture). Builder + 3 tests (fixture `module` = build unique), 2 vues (`text`/`caseless`). | Verdict XerOCR sur **données réelles** : en `caseless` **`deu_latf` gagne** (CER 0,075) ; `easyocr` excellent en **français** mais nul en Fraktur (0,21 agrégat). **Significativité Friedman** (n=30) : à 4 Tesseract text:cer p=0,072 (non sig.) → **avec EasyOCR p≈0 = SIGNIFICATIF** (l'écart d'architecture crée la différence détectable). Effet **langue×moteur** visible au par-document. Réalise le « mini-corpus de référence » de `CLAUDE.md §10`. | Moteurs atteignables sous la politique réseau : **Tesseract** (apt+GitHub) **+ EasyOCR** (modèles GitHub) ✓ ; **Pero/Kraken/docTR** = paquets OK mais **poids 403** (Drive/Zenodo/HuggingFace). Images/ALTO non committés (poids) → *live* = test `live` ; strate langue par-doc = enveloppe T7 ; **`by-engine` désormais justifié** (section à construire) ; `synthesis` différé |
| D-021 | 2026-06-02 | S4.b.3 by-engine | Construire `by-engine` sans **dupliquer l'overview** ni **copier les 14 métriques spéculatives** du design ? | **EngineSection** (couche 7) : une table **triée par CER** (verdict « qui gagne ») + colonne **dispersion** = `cer` min·médiane·max **par-document** (la fiabilité que l'agrégat masque). Métriques **réelles** seulement ; enregistrée overview→**by-engine**→by-document→crosses. | La **vérif-plan** a attrapé le risque : l'overview montre déjà moteurs×métriques par vue → un `by-engine` descriptif serait **redondant** (§5.3) ; et la réf design est **en avance sur la donnée** (philologie/calibration/économie non calculées). Le **tri + la dispersion** sont l'info **neuve** (ni overview ni par-document ne la donnent) ; un classement chiffré ≠ prose (narratif reste supprimé). | reste S4.b : **crosses** (à styliser au design) + **synthesis** (différé T7) → ensuite repointer « Prochaine → S5 » |
| D-022 | 2026-06-02 | S4.b.4 + clôture S4 | Styliser `crosses` au design et **clore S4** (vues rapport) ? | **CrossEngineSection** restylée `table.data` : clé `text:cer:significance_p` **éclatée** en colonnes **Vue/Métrique** + **verdict** factuel (« significatif » si p<0,05, en fern ; sinon « non sig. » ; `None`→« — »). **S4 clos** : overview/by-engine/by-document/crosses au design ; **synthesis différé T7**. | Le verdict est une **fonction auditable** de la p-value (pas de la prose, narratif §6 respecté) ; la clé brute était cryptique → Vue/Métrique + verdict = lecture directe. Clôt S4.b → **« Prochaine » repointée S4b→S5** (`CLAUDE §0` + roll-up + `NEXT_SESSION`), résolvant la **dette de pointeur** signalée depuis D-020. | reste **synthesis** (T7, avec ses métriques riches) ; `crosses` pourra gagner les comparaisons **par paires** quand le besoin existera |
| D-023 | 2026-06-02 | S5 (vérif) + clôture axe Space | « Enchaîner S5 » : que reste-t-il du durcissement public ? | **Vérif-plan** : S5 est **déjà implémenté + testé** (le « partiel » du roll-up était périmé) — mode public **enforced à l'API** (`runs.py:160`, cloud→403, source unique `CLOUD_KINDS`) · rate-limit durci (purge IP inactives, global) · CSRF · CSP `'self'` · upload double-cap. **Pas** de module `public_mode.py`/`uploads.py` séparé : la logique vit **avec son consommateur** (anti-Picarones, ≠ 6 modules `security_*`). Seul trou comblé : **test 413** (upload > `MAX_ZIP_BYTES`, monkeypatch). **S5 → axe Space S1–S5 complet.** | Bâtir des modules séparés aurait été **spéculatif** (§5.3) : le durcissement existe déjà, seule la **couverture de test** du plafond externe manquait. Repointe **« Prochaine » S5→T5** : l'axe Space est clos ; **S6 attend l'axe moteur** — la suite est côté **moteur** (segmentation / métriques). | **Pivot d'axe** : reste **T5** (structure/seg → débloque S6-seg) · **T6** (extensibilité) · **T7** (surfaces internes/métriques → débloque `synthesis` + S6-imp). T5 vs T7 = priorité produit. |

| D-024 | 2026-06-03 | T7 (métriques riches) | Acter les 3 premières métriques T7 livrées (PR #25-#27) + réconcilier le roll-up | **3 métriques philologie/profil d'erreur** câblées sur le benchmark **réel** BNL (Fraktur), chacune vérifiée informative *avant* câblage et figeant sa trouvaille par un test BNL micro+macro : **`cer_diplo`** (#25 — CER après repli ſ long→s appliqué symétriquement ; isole la pénalité typographique des Fraktur `frk`/`deu_latf`, ~12 % de leur erreur ; reste pur, réutilise `_edit_distance` + profil `minimal` couche 2) · **`diacritic_err`** (#26 — fraction des diacritiques de la réf mal reconnus par alignement `rapidfuzz.editops` ; révèle que les modèles germaniques butent sur ~80 % des umlauts vs ~12 % pour `fra`/`easyocr` ; **introduit `rapidfuzz` en prod** — sanctionné par la tranche qui l'introduit, fichier dédié `diacritics.py`, `text.py` reste pur D-007) · **`del_rate`/`ins_rate`** (#27 — profil d'erreur, réutilise `_align`/`_error_rate`, **aucune dép.** ; `easyocr` a le pire `ins_rate` → il **hallucine** là où CER/WER le noyaient ; `sub_rate` écarté car dérivable `wer−del−ins`, §5.3). Les sections génériques affichent les colonnes **sans rendu modifié** (dividende du design). Roll-up : couche 3 + ligne T7 → **🔨 partiel**. | Surface incrémentale stricte (§5.3 : additive, budget, élagage). **Ligatures écartées** (1 seule dans la GT BNL → non informatives, branche `t7-ligatures` au nom trompeur) au profit du profil d'erreur, après vérif des données. T7 reste ⏳ pour **importeurs cœur / longitudinal / `synthesis`** (ce dernier attendait précisément des métriques riches). | matérialise la ligne « Philologie/Taxonomie/… » de §3 (T7+) |

| D-025 | 2026-06-03 | T5 squelette segmentation | Bâtir le squelette ambulant de la tranche segmentation (pleine profondeur, largeur minimale) sans rien casser de l'enveloppe ? | **Squelette bout-en-bout, tout `precomputed`** : C1 `domain/layout.py` (`CanonicalLayout` + `LayoutPage/Region/Line/Word/Geometry/BBox/Point`, type **pivot** dimensionné plein-scope, géométrie en `domain` — F-1 option b) · C5 `adapters/layout/precomputed.py` (source LAYOUT régions-seules + recognizer **par région** clé `region_id`) · C4 `pipeline/fanout.py` (`run_region_fanout` : boucle régions → recognizer 1×/région → LAYOUT rempli, **échec partiel toléré**, ordre de lecture préservé) · C3 `metrics/layout.py` (`region_cer` (LAYOUT,LAYOUT) = CER par région micro-agrégé page ; **niveau absent → `None`**) + loader `LAYOUT` (`representations.py`). 6 tests bout-en-bout + unitaires verts. | **Le contrat `Module` ne bouge pas** (renvoie 1 artefact/type ; le fan-out boucle dans l'exécuteur) → « test conceptuel » T5 tenu : T5 n'**ajoute** que. Choix de largeur minimale conformes au guide `ANALYSE_T5_SEGMENTATION.md` : LAYOUT sérialisé **JSON** (pas de mapping ALTO au squelette — épaississement F), assemblage = **LAYOUT rempli** (pas ALTO_XML), pas de crop/PIL (precomputed), projecteur `layout→text`/`ProjectionSpec` **non ajoutés** (0 consommateur dans cette tranche, §5.3). Câblage corpus réel + informativité (§H du guide) différés à un épaississement (stratégie « squelette synthétique d'abord »). | matérialise le backlog `CanonicalLayout` (`CLAUDE.md`) + lève `MIGRATION_COUCHE_2.md` L10 (forme confirmée au build) |

| D-026 | 2026-06-03 | T5 épaississement (ALTO→layout) | Premier épaississement après le squelette : quel concept unique, avec consommateur de production ? | **`alto_to_layout`** (C2, `formats/alto/layout_map.py`) — projette `AltoDocument` parsé vers `CanonicalLayout` neutre (régions/lignes/mots/géométrie bbox+polygone/ordre de lecture ; `id` manquants synthétisés `region_<n>`, déterministe). **Consommateur de production** : `load_representation(LAYOUT)` détecte ALTO (1ᵉʳ octet `<`) vs JSON → une **GT de mise en page ALTO réelle** est chargeable et `region_cer` tourne dessus (test bout-en-bout). | Un seul concept (« le modèle neutre lit du vrai ALTO »), avec un **vrai consommateur** (≠ mapper testé seul, §5.3) : c'est ce qui débloque R-2 (GT layout réelle) vers l'informativité. Différés (chacun sa tranche) : **assembleur inverse `layout→ALTO_XML`** (le pendant ; le fan-out n'émet encore qu'un LAYOUT rempli), **mapper PAGE**, **dé-césure** `HypPart1/2` (concern projection `layout→texte`), **alignement IoU** (l'appariement reste par `id`), **segmenteur réel + crop**. | avance le pont `CanonicalLayout↔ALTO` du guide `ANALYSE_T5_SEGMENTATION.md` §G-2 |

| D-027 | 2026-06-03 | T5 assemblage (layout→ALTO) | Boucler le contrat `segmentation → reconnaissance → assemblage (LAYOUT→ALTO_XML)` (`CLAUDE.md` §3) ; **où** placer l'assembleur ? | **`layout_to_alto`** (C2, pendant inverse de `alto_to_layout` ; mots→`<String>`, sinon texte segmenté sur les blancs ; ordre de lecture appliqué ; octet-stable via `write_alto`) **+ `AltoAssembler`** Module en **couche 5** (`adapters/layout/assembler.py`) : LAYOUT rempli → ALTO_XML. Consommateur bouclé : l'ALTO assemblé est **rechargé comme layout** par `load_representation` (sniff ALTO) → `region_cer`. | **Placement dicté par les garde-fous d'archi** : `test_pipeline_imports_are_allowed` **interdit `pipeline → formats`** ; l'assembleur dépend de `write_alto` (formats) → il **ne peut pas** vivre en `pipeline`. Or `CLAUDE.md` §3 liste « constructeur d'ALTO » comme un **Module** (brique pluggable) et la couche 5 **peut** importer `formats` → l'assembleur est un **adapter Module**, placement à la fois légal et conceptuellement juste. Un seul concept (« assembler le layout en ALTO »), consommateur réel (≠ test seul). Différés : mapper PAGE, dé-césure, IoU, segmenteur réel, **wiring spec complet** (segmentation→fan-out→assemblage via une `PipelineSpec` unique). | clôt le pont `CanonicalLayout↔ALTO` du guide §G-2 ; lève le différé « assembleur » de la DoD couche 2 |

| D-028 | 2026-06-03 | T5 wiring spec déclaratif | Faire orchestrer les 3 étages de segmentation par une **`PipelineSpec` unique** (modules via factory), pas par des appels directs dans les tests — **comment** déclarer le fan-out dans une spec DAG linéaire ? | **Drapeau déclaratif `PipelineStep.fanout: bool`** (C1, + `model_validator` : `fanout` exige `LAYOUT`+`IMAGE` en entrée, `LAYOUT` en sortie). L'**exécuteur** (C4) branche sur `step.fanout` → délègue à **`execute_region_fanout`** (C4 : charge le LAYOUT régions-seules, fan-out reconnaissance, **persiste** le LAYOUT rempli en JSON, renvoie l'artefact ; provenance estampillée comme une étape normale). **3 builders** au registre (C6) : `precomputed_layout`, `precomputed_region`, `alto_assembler`. Test bout-en-bout : 1 spec → segment → fanout → assemblage → `ALTO_XML` rechargé en layout → `region_cer`. | Le `Module` Protocol **ne bouge toujours pas** (le fan-out reste de l'orchestration C4 ; le module renvoie 1 artefact/type). Drapeau `bool` (≠ `fanout_over: ArtifactType`) car le seul consommateur fan-out est « par région d'un LAYOUT » — typer plus serait spéculatif (§5.3). **Collision de nom résolue** : `PrecomputedLayoutSource.name` passe de `precomputed:layout` (kind `precomputed`, en conflit avec l'OCR texte) à **`precomputed_layout`** (kind distinct). Différés : mapper PAGE, crop réel, IoU, câblage corpus réel. | retire de l'exécuteur la mention « fan-out = tranche ultérieure » ; prouve l'orchestration par déclaration |

| D-029 | 2026-06-03 | T5 mapper PAGE | Symétrie ALTO : projeter PAGE XML vers le modèle neutre, avec consommateur réel. | **`page_to_layout`** (C2, `formats/pagexml/layout_map.py`) — conventions PAGE projetées vers `CanonicalLayout` : géométrie **polygones** (`coords` → `Geometry.polygon`, pas de bbox), **ligne sans mots** (`Line.words=()`), **ordre de lecture en arbre** aplati via `flatten()`, régions non-texte → `region_type` reprenant le label PRImA. **Consommateur** : `load_representation(LAYOUT)` distingue désormais **PAGE vs ALTO** au marqueur de racine (`PcGts`/`pagecontent` = PAGE) → GT layout PAGE réelle + `region_cer` (test bout-en-bout). | Même patron que `alto_to_layout` (D-026), un seul concept, consommateur de production. **Sniff XML affiné** : ALTO et PAGE commencent tous deux par `<` → désambiguïsation sur le marqueur de racine (head 4 Ko, insensible à la casse), déterministe. `_Counter` dupliqué (6 lignes) plutôt qu'un module partagé — extraire pour 2 appels serait sur-ingénierie. Différés : crop réel, IoU, câblage corpus réel. | lève le dernier mapper du différé DoD couche 2 ; ALTO **et** PAGE alimentent maintenant le même `CanonicalLayout` |

| D-030 | 2026-06-03 | T5 informativité corpus réel | Avant de s'appuyer sur l'axe structure : `region_cer` est-il **correct, non-trivial et non trompeur** sur de **vraies** données (réflexe §H du guide) ? | **Câblage sur 4 producteurs réels** (`tests/formats/fixtures` : Gallica ALTO v2, Tesseract ALTO v3, Transkribus PAGE, eScriptorium PAGE) via `load_representation`. **Findings réels** : (a) le modèle neutre porte la **diversité réelle** — bbox+mot (ALTO) vs polygone+ligne (PAGE), imbrication `ComposedBlock`+illustration (Gallica), **corps + marginalia** (eScriptorium) ; (b) `region_cer` = 0 sur identité réelle (applicable, pas `None`), `1/53` quand la marginalia (4 car. sur 53) est mal lue, `4/53` quand la **région est omise** (segmentation ratée pénalisée), `None` si niveau texte absent (pas un faux 1.0) ; (c) tout passe par le **vrai runner** `evaluate_run`. | Pas de fabrication : l'hypothèse dégradée est une **perturbation contrôlée d'une GT réelle**, clairement étiquetée (≠ run d'OCR réel). Le **fetch BNL live** reste hors-scope (politique réseau ; les fixtures producteurs committées **sont** la donnée réelle). Aucun code de prod ajouté — c'est une **preuve de câblage** (test). | valide l'axe structure « real-data-ready » ; consomme la stratégie « synthétique d'abord, réel au câblage » (D-025) |

*Prochaines entrées : à ajouter au fil des tranches, dans le même commit que le code.*

---

*Référence : ce plan relie les guides par couche en un parcours de tranches. Enveloppe
(§1) durable ; surface (§3 détail) à confirmer au build. Verdicts de surface marqués
PROVISOIRE. Détail d'avancement = `DoD vivante` de chaque `COUCHE` doc (autorité) ;
ce plan = index + orchestration + journal.*
