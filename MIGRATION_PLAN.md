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
| 1 `domain` | ✅ **vert** | `xerocr/domain/MIGRATION_COUCHE_1.md` §DoD |
| 2 `formats` | ✅ **vert** | `xerocr/formats/MIGRATION_COUCHE_2.md` §DoD |
| 3 `evaluation` | 📋 plan, 0 code | `xerocr/evaluation/MIGRATION_COUCHE_3.md` §DoD |
| 4 `pipeline` | 📋 analyse | `xerocr/pipeline/ANALYSE_COUCHE_4.md` §DoD |
| 5 `adapters` | 📋 analyse | `xerocr/adapters/ANALYSE_COUCHE_5.md` §DoD |
| 6 `app` | 📋 analyse | `xerocr/app/ANALYSE_COUCHE_6.md` §DoD |
| 7 `reports` | 📋 analyse | `xerocr/reports/ANALYSE_COUCHE_7.md` §DoD |
| 8 `interfaces` | 📋 analyse | `xerocr/interfaces/ANALYSE_COUCHE_8.md` §DoD |
| **T0 fondations** | ✅ **clos** (§9) | 163 tests / 95 % · mypy strict · ruff · 6 garde-fous |
| **T1 squelette ambulant** | ⏳ pas commencé | critère inter-couches §3-T1 |

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
T4  serve (web) ───────────────────────────────────────▶  xerocr serve
      │   create_app · security/ · JobStore+SSE · annulation réelle
T5  STRUCTURE (segmentation / layout)  ★ ambition nouvelle ─▶ métriques structurelles
      │   CanonicalLayout · fan-out région · segmenteur de référence
T6  EXTENSIBILITÉ TIERCE  ★ ambition nouvelle ─────────▶  charger un module hors-arbre
      │   entry-points xerocr.modules · 1 plugin de référence
T7+ SURFACES INCRÉMENTALES ────────────────────────────▶  1 importeur / métrique / section par tranche
          corpus IIIF/Gallica/… · longitudinal · philologie · taxo · économie · observabilité · Docker/release
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

### T4 — `serve` (web)

| | |
|---|---|
| **Objectif** | Exposer le cœur (T1-T3) via le web, avec l'**enveloppe de transport plein-scope**. |
| **Traverse** | 8 (`create_app()` factory · routers `benchmark`(SSE)/`corpus`/`reports`/`home` · package `security/` : CSRF/CSP/rate-limit/uploads/**mode public** · DTO transport · panneau de pilotage **mince**) · 6 (`JobRunner` + annulation coopérative) · 5 (`JobStore` en `adapters/storage` **avec `job_events`/SSE réabsorbés**) |
| **Élimine** | effets de bord d'import (factory) · 2 JobStore→1 (SSE conservé) · sécurité éclatée 7 modules→1 package · annulation fantôme → `RunControl`/`Deadline` de bout en bout · SPA lourde→panneau mince |
| **Validation** | tests sécurité **verts d'abord** (CSRF→403, `..`/symlink→rejet, zip-bomb→échec, cloud en mode public→403) · un `cancel` interrompt réellement · reprise SSE `Last-Event-ID` |
| **Diffère** | importeurs exotiques · longitudinal · `/metrics` |

### T5 — Structure (segmentation / layout) ★ ambition nouvelle

| | |
|---|---|
| **Objectif** | **Matérialiser** ce que l'enveloppe réservait depuis T1. La **preuve que le dimensionnement précoce a payé** — zéro réécriture des couches 1-4. |
| **Traverse** | 1 (`CanonicalLayout` + parties en `domain`) · 2 (mappers `alto/page→layout`) · 3 (projecteur `layout→text` + **shapely** confiné + `region_detection`/`line_detection`/`reading_order`/`geometry_coverage`) · 4 (**fan-out** : segmentation → reconnaissance par région → réassemblage + routage par type de bloc) |
| **Ambition** | `segmentation (IMAGE→LAYOUT) → reconnaissance par région → assemblage (LAYOUT→ALTO)` + segmenteur de référence (starter pack) |
| **Validation** | `region_id` exercé · `RunResult` accueille une métrique `(LAYOUT,LAYOUT)` **sans modif de contrat** · golden **ALTO+PAGE** · round-trip fidélité |
| **Test conceptuel** | si T5 force à changer `RunResult`/registre/`Module`, le dimensionnement de T1 était faux. Attendu : elle ne fait qu'**ajouter**. |

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
| F8 | 2 JobStore (SSE perdu) | **T4** | 1 store + SSE réabsorbé avant suppression legacy |
| F9 | Bugs latents masqués par mocks | **T7 importeurs** | corrigés + test `live`/`network` |
| F10 | Provenance dormante | **T1** | câblée dans l'executor |
| F11 | Annulation/deadline non câblées | **T3**→**T4** | `RunControl`/`Deadline` réels de bout en bout |
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
| Sécurité in-process (mode public) | T1 | T4 + T6 |
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

*Prochaines entrées : à ajouter au fil des tranches, dans le même commit que le code.*

---

*Référence : ce plan relie les guides par couche en un parcours de tranches. Enveloppe
(§1) durable ; surface (§3 détail) à confirmer au build. Verdicts de surface marqués
PROVISOIRE. Détail d'avancement = `DoD vivante` de chaque `COUCHE` doc (autorité) ;
ce plan = index + orchestration + journal.*
