# Plan de migration — Couche 3 (`evaluation/`) : Picarones → XerOCR

> Statut : **plan acté**, implémentation à venir. Lecture seule du code Picarones.
> Ce document fige les **contrats transverses** (enveloppe) ; le **remplissage**
> suit des tranches verticales (cf. §2). Aligné sur `CLAUDE.md` (deux axes,
> tranches, narrative supprimé, `CanonicalLayout` différé).

---

## 1. Objectif & périmètre

La couche 3 calcule des **métriques** sur les sorties des pipelines (OCR/HTR/VLM,
OCR+LLM) face à une vérité-terrain, et produit un **`RunResult`** sérialisable +
les données du rapport. **Migration complète** (pas un MVP réduit) : on conserve
toutes les vraies métriques ; on ne supprime que le **mort / doublon / mal placé**.

Dépend des couches mergées : **domain** (`ArtifactType` dont `LAYOUT`, `Artifact`,
`EvaluationView`/`MetricSpec`/`EvaluationSpec`, `RunManifest`, `Corpus`/`Document`)
et **formats** (ALTO/PAGE riches, `_geometry`, `text/normalization`).

Ne fait **ni I/O, ni rendu, ni exécution de moteur** : ce qui violerait ça sort
vers `adapters/` / `reports/` / `pipeline/`.

---

## 2. Principe directeur — deux axes, tranches verticales

Rappel `CLAUDE.md` §2/§4. **Deux axes strictement séparés** :

| Axe | Quand | Ici |
|---|---|---|
| **Enveloppe** (contrats, types pivots, points d'extension) | **Dimensionnée plein-scope, maintenant** | registre type-driven, `RunResult`, deux formes de métriques, `Protocol Section` du rapport, slot `ArtifactType.LAYOUT` |
| **Surface** (métriques, sections, importeurs) | **Incrémentale, minimale, élaguée** | une métrique/section à la fois, dans un budget |

**Tranches verticales** (≠ « finir la couche 3 horizontalement ») : couches 1-2
faites horizontalement (stables) ; couche 3+ par **squelettes ambulants** fins de
pleine profondeur. La **première tranche** prouve que l'enveloppe tient avant d'y
verser des features.

**Cas particulier du rapport (cadre vs contenu)** : le **cadre** conceptuel
(`Protocol Section` unique, consommation directe du `RunResult`, un seul format)
est conçu **plein-scope dès maintenant** ; le **contenu** (nombre de sections,
visualisations) grossit **au rythme des métriques** qui l'alimentent. Construire
toutes les sections d'avance = bâtir du rapport **en avance sur ses données** =
l'accrétion qui a alourdi Picarones. Le HTML basique du squelette **n'est pas
jetable** : c'est la première section vraie, sur le cadre définitif.

---

## 3. Noyau verrouillé (enveloppe, plein-scope maintenant)

1. **Registre unique type-driven.** Suppression des 4 systèmes parallèles de
   Picarones (hooks `①`, registre module-level `③`, `@register_lever` `④`) ;
   reste le **registre instanciable** (`②`), sélection **100 % par `input_types`**.
2. **Deux formes de métriques** : **par-document** `(ref, hyp)` et **inter-moteurs**
   `(EngineReports)`. Agrégation par-moteur **générique** (scalaires) +
   **agrégateur custom co-localisé pour les structs** (dict — pas un cas rare).
3. **`DocContext` / `CrossEngineContext`** : sac d'entrées **extensible** par forme.
4. **Fiche + fonction co-localisées** ; **décorateur pur** (construit un `Metric`,
   ne mute aucun global) + **collecte explicite par sous-paquet**.
5. **Sécurité scientifique obligatoire** (dette C) : `safe_ratio`/`safe_mean`
   (rendent `None` sur vide) ; agrégation **exclut `None`** + **expose le *support***.
6. **`scipy` en dépendance dure** (Wilcoxon/Friedman/OLS validés).
7. **`shapely` confiné** (`evaluation/geometry.py`), invoqué **seulement pour les
   polygones**, **dégradable** (`backend="shapely"` → repli bbox + warning).
   **Ajouté avec la tranche structure** (§10), pas maintenant.
8. **Persistance** : `schema_version` sur le **document `RunResult`** (rapport/compare)
   + **store longitudinal en lignes *tidy*** (additif). Complémentaires (§8).
9. **Déterminisme bit-à-bit** ; **clés de sortie stables** (renommer un fichier =
   libre ; renommer une clé de métrique = interdit, contrat dur avec rapports/JS).

---

## 4. Première tranche = squelette ambulant (axe texte)

Le premier pas n'est **pas** le `CanonicalLayout` — c'est un **squelette fin de
pleine profondeur** sur l'axe texte (`CLAUDE.md` §4) :

```
corpus pré-calculé (texte) → 1 CER → RunResult → HTML basique (1 section) → CLI `demo`
```

Il **exerce l'enveloppe complète** (registre, `RunResult`, runner, `Protocol Section`)
avec **une seule métrique scalaire** (CER). Aucun `CanonicalLayout`, aucun shapely,
aucune structure. Objectif : prouver que les contrats s'emboîtent de bout en bout.
Puis on **épaissit l'axe texte** (WER/MER, profils, stats scipy, cross_engine,
compare) avant d'ouvrir l'axe structure.

---

## 5. Le registre (contrat — enveloppe)

- **`domain/evaluation.py:MetricSpec`** = contrat de type **minimal** (`name`,
  `input_types`, `description`, `higher_is_better`) — déjà présent.
- **La couche 3 enrichit** (métadonnées opérationnelles, hors domain) : `level`/forme,
  `profiles`, `tags`, `requires`, `backend`, `unit`, `cost_hint`, `spec_version` —
  **chacune avec un lecteur nommé**. Co-localisée avec la fonction.
- **Signatures** : `fn(ctx: DocContext) -> …` et `fn(ctx: CrossEngineContext) -> …`.
  Séparation **garantie par les signatures**, pas par une police AST.
- **Profils** (`profiles.py`) : liste nommée **ou** sélecteur de tags simple
  (`rapide`, `avancé`, …). Pas d'algèbre. Vocabulaire de tags petit et validé.

---

## 6. Le runner (deux passes)

`evaluation/runner.py` (+ logique de calcul **rapatriée** de `app/services/_benchmark_*` —
l'app *appelle*, ne *calcule* plus) :
1. **Par-document** : `select(input_types)` → `DocumentMetric` sur `DocContext` ;
   `None` = non applicable (skip).
2. **Agrégation par-moteur** : générique (scalaires) + **custom (structs)** ;
   `None` exclu ; **support** calculé.
3. **Inter-moteurs** : `CrossEngineMetric` sur `CrossEngineContext` → **écrit dans `RunResult`**.

---

## 7. Défenses (sécurité scientifique, dette C)

Couches : `input_types` (gratuit) · `safe_*` (vide → `None`) · préconditions
`requires` (le runner saute) · **test générique** d'entrées dégénérées · **golden**
sur fixtures réelles **ALTO + PAGE + texte** · agrégation `None`-exclu + support ·
revue. Risque **présent dès l'axe texte** (ratios sur vide) → `safe_*` jour 1 ;
amplifié à l'axe structure (mélange ALTO/PAGE).

---

## 8. Résultat & persistance

- **`evaluation/result.py:RunResult`** (ex-`benchmark_result`, dégonflé) = contrat
  de sortie unique, **dimensionné plein-scope** (porte taxonomy/NER/structure dès
  sa conception, même si la 1ʳᵉ tranche n'écrit qu'un CER), avec **`schema_version`** + upcaster.
- **cross_engine écrit dans le `RunResult`** ; le rapport ne fait que lire.
- **Store longitudinal *tidy*** (lignes `(run, moteur, métrique, valeur, spec_version)`),
  en `adapters/storage` (I/O hors couche 3). Ajout de métrique = additif.
- **Réconciliation note couche 2** : « le jeu de champs fait foi » = même esprit que
  le tidy pour les **ajouts** ; `schema_version` couvre les **changements structurels**
  du document. Ne pas laisser « pas de version » déborder sur le document `RunResult`.
- **Rapport interactif (what-if) — QUESTION OUVERTE, à trancher à sa tranche (tardive)** :
  un rapport **filtrable** (ex. « exclure les docs hallucinés » → recalculer les agrégats)
  est une feature **tardive, sans consommateur aujourd'hui** → on **ne fige pas son mécanisme
  ici** (`CLAUDE.md` §9 : ne pas figer une forme avant son consommateur). Constat utile :
  `RunResult` **porte déjà les résultats par-doc** (`RunDocumentResult`) → **aucun changement
  d'enveloppe forcé maintenant**. Deux mécanismes à départager **à la tranche** :
  **(a, recommandé)** le **runner pré-calcule** les agrégats des états what-if pertinents
  (p. ex. via des `EvaluationView` dédiées) → le rapport **sélectionne**, ne calcule jamais
  (invariant « le rapport ne recalcule jamais » respecté à la lettre ; marche pour générique
  *et* custom) ; **(b)** ré-agrégation côté client sur les valeurs par-doc (continu, mais 2ᵉ
  implémentation à golden-tester, limitée aux agrégateurs simples). *(Soulevé par
  `reports/ANALYSE_COUCHE_7.md` §2.7 ; décision au build, pas ici.)*

---

## 9. Le rapport — cadre plein-scope, contenu incrémental

- **Cadre (maintenant)** : un **`Protocol Section` typé unique**, consommant le
  `RunResult` **directement** (pas de data-layer qui ré-agrège — anti-pattern
  Picarones), un seul format, budgets.
- **Contenu (incrémental)** : 1 section au squelette (overview/engines/CER) ;
  on **ajoute des sections à côté** au rythme des métriques (documents, crosses,
  structure…). Jamais de section en avance sur sa donnée.
- **Pas de `reports/narrative/`** (supprimé, `CLAUDE.md` §6) : chiffres et tableaux
  bruts, aucune prose générée.
- **Interactivité (what-if) = sélection, jamais re-mesure** (cf. §8, **question ouverte**) :
  si un rapport filtrable est construit (tranche tardive), il **sélectionne** une vue/projection
  ou ré-agrège un sous-ensemble — **jamais** une re-mesure côté client ; l'**inférentiel**
  (Wilcoxon/IC) reste gelé sur le corpus complet. **Mécanisme tranché à sa tranche**
  (candidat = projections pré-calculées par le runner).

---

## 10. `CanonicalLayout` & axe structure — ENVELOPPE, matérialisés à la 1ʳᵉ tranche structure

**Différé, par discipline** (`CLAUDE.md` §3/§6) — *pas le premier pas*.

- **Réservé maintenant (enveloppe)** : `ArtifactType.LAYOUT` existe + `region_id`
  optionnel sur `Artifact`. Le registre (générique sur les types) et le `RunResult`
  (générique sur les métriques) **accueillent déjà** une métrique `(LAYOUT, LAYOUT)`
  dès que des artefacts `LAYOUT` existeront — **sans** connaître les champs du type.
- **Matérialisé plus tard** : le **type concret** `CanonicalLayout` (en `domain`)
  + les **mappers** `alto/page → layout` (formats) + le projecteur `layout → text`
  + les **métriques structurelles** (`region_detection`, `line_detection`,
  `reading_order`, `geometry_coverage`) + **shapely** — tout ça naît à la
  **première tranche *structure***.
- **Déclencheur = la première tranche structure**, qui peut être l'**évaluation
  structurelle** (couche 3 : mappers + métriques, sur des sorties ALTO/PAGE de
  n'importe quel pipeline) **ou** la **segmentation** (couche 4), selon laquelle on
  construit en premier. Le type **vit en `domain`** dans les deux cas ; « couche 4 »
  est un raccourci pour « la tranche où son premier consommateur apparaît ».
- **Pourquoi pas maintenant** : un type sans consommateur = code mort + champs figés
  **avant** son consommateur = spéculatif (garde-fou *« pas de consommateur =
  supprimé »*). Le différer est **plus sûr**, pas moins.

**Esquisse cible** (à *confirmer* avec le consommateur, **ne pas figer maintenant**) :
sur-ensemble fidèle des types couche 2 — `Geometry{bbox?, polygon?, baseline?}`,
`Word` optionnel (+ hyphénation), `Line{text, words?, geometry?}`,
`Region{region_type?, kind(text|generic), regions(imbrication)}`, `ReadingOrder`
**en arbre** (mappe le PAGE ; ALTO = groupe plat = ordre des blocs), `LayoutPage`,
`CanonicalLayout{pages, source_format}` + `has_word_level`. **Bonne nouvelle couche 2** :
l'ALTO de XerOCR porte déjà `baseline` + `block_type` → métriques structurelles
applicables sur ALTO aussi (pas systématiquement `None`).

---

## 11. Inventaire source → cible (Picarones `evaluation/`, 93 fichiers)

**Supprimés** — 4 registres + plomberie (`metric_hooks`, `builtin_hooks`,
`builtin_metrics`, `metric_registry`, 4×`*_hooks`), doublon (`search`), morts
(`equivalence_profile`, `alto_metrics`, `cost_projection`, `ner_backends`,
`difficulty`, `module_policy`), `normalization` (consolidé en `formats/text`),
**`levers`** (4ᵉ registre, synthèse type-narrative → **abandonné**, narrative supprimé).
⚠️ Supprimer une métrique n'est pas local : nettoyer ses références côté reports/JS/CSV
(ex. clé `difficulty_score`).

**Changés de couche** — `history` (SQLite) → `adapters/storage` ; `cdd_render` (SVG),
`worst_lines` → `reports` ; ré-exécution moteur de `robustness` → `pipeline`.

**Modifiés** — renommages (`benchmark_result`→`result`, `evaluation_engine`→`runner`,
`_diff_utils`→`diff`), splits >400 LOC (`modern_archives`, `roman_numerals`,
`numerical_sequences`, `inter_engine`), structure réécrite sur `LAYOUT`
(`layout`→`region_detection`, `reading_order`, `alto_structural`→`geometry_coverage`),
dédoublonnage (`searchability` absorbe `search`), `reliability`→`multirun_stability`.

**Gardés** — noyau métier (CER/WER, philologie, inter-moteurs, économie, image,
longitudinal) ; **clés de sortie inchangées**.

**Nouveaux** — `profiles.py`, `metrics/_helpers.py` (`safe_*`) [axe texte] ;
`geometry.py`, `structure/region_detection.py`, `structure/line_detection.py`,
`projectors/layout.py`, `gt_types.py` [tranche structure].

**Organisation cible** : `metrics/{text, philology/, structure/, cross_engine/,
economics/, image/, longitudinal/}`, `statistics/`, `views/`, `projectors/`.

---

## 12. Risques de transfert Picarones → XerOCR

1. `reading_order` sans source (Picarones) → **résolu couche 2** (arbre `ReadingOrder`
   côté PAGE ; ALTO = ordre de bloc → groupe plat dans le mapper).
2. **Agrégateurs custom** (confusion/taxonomie/calibration) — pas des moyennes (§6).
3. **Clés de sortie = contrat dur** avec reports/JS/compare.
4. `benchmark_result`→`RunResult` : ~30 consommateurs — beaucoup meurent (shim,
   workflows), migrer reports + web + compare **en bloc**.
5. Consolidation `normalization` : **sans danger** (l'eval n'en définissait aucun).

---

## 13. Explicitement laissé au codage (sous test)

Intérieur des métriques ; contenu des profils + vocabulaire de tags ; liste des
métriques structurelles PAGE-natives ; découpes des fichiers >400 LOC ; coutures
(pré-passe stats corpus → `DocContext` pour `rare_tokens` ; alimentation historique
→ longitudinal/`baseline_comparison`) ; champs concrets du `CanonicalLayout` (§10).

---

## 14. Tests & budgets

- **Architecture** : étendre la whitelist `evaluation/` (**+scipy maintenant** ;
  **+shapely/jiwer/rapidfuzz/numpy/PIL au fil des tranches qui les introduisent**) ;
  `no-side-effect-import` (décorateur = valeur pure) ; `file-budgets`.
- **Golden** : `RunResult` canonique ; **ALTO+PAGE+texte** à la tranche structure ;
  déterminisme bit-à-bit.
- **Sécurité** : test générique d'entrées dégénérées ; CER/WER vs `jiwer` ;
  round-trip de fidélité format→`LAYOUT` (à la tranche structure).

---

## 15. Ordre d'implémentation (tranches verticales)

1. **Squelette texte** : corpus pré-calculé → CER → `RunResult` (plein-scope) →
   HTML basique (1 section, cadre `Protocol Section`) → CLI `demo`. Registre +
   `DocContext` + `runner` (1 métrique) + `safe_*`.
2. **Épaissir l'axe texte** : WER/MER + portage du noyau texte (clés stables),
   `profiles`, statistiques (**scipy**), `cross_engine` (écriture `RunResult`), `compare`.
3. **Tranche structure** : `CanonicalLayout` (domain) + mappers `alto/page→layout`
   + projecteur `layout→text` + **shapely**/`geometry.py` + `region_detection`/
   `line_detection`/`reading_order`/`geometry_coverage` + golden ALTO/PAGE.
4. **Store longitudinal *tidy*** (via `adapters/storage`) + reste des métriques
   (philologie, économie, image, longitudinal) — une par une, en budget.

---

## DoD vivante (couche 3) — **autorité de détail** ; le `MIGRATION_PLAN.md` indexe

> Tri-état : `[x]` fait **+ preuve** · `[ ]` à faire · `[~]` différé/réserve + raison.
> Maj dans le **même commit** que le code. **Statut : ✅ T2** — `RunResult` plein-scope + registre type-driven + runner verts ; **CER/WER/MER** (parité jiwer) + profils de normalisation + stats `scipy` + `cross_engine` **livrés**. **+ T5 structure** : `region_cer` `(LAYOUT,LAYOUT)` + **`region_detection`** (F1 IoU de boîte, coords relatives — neutralise mm10/px ; **sans shapely**) + loader `LAYOUT` (JSON/ALTO/PAGE) + **projecteur `layout_to_text`** avec **exécution `ProjectionSpec`** dans le runner (un LAYOUT noté par les métriques texte ; réserve §9 `ProjectionSpec` levée ; vrai benchmark BNL ABBYY-vs-Tesseract en test `live`, F1 détection 0.35@0.5). — *preuves : `tests/evaluation/test_projection.py`, `…/test_projection_real_bnl.py`, `…/test_region_detection.py`*. **+ T7 philologie `mufi_err`** (`metrics/philology.py`) : taux d'erreur sur les caractères MUFI/médiévaux (PUA + Latin Extended-D + `ſ`/`þ`/ligatures), même alignement `rapidfuzz` que `diacritic_err`, `None` si la réf n'en porte aucun ; ajouté au socle → registre = `cer, cer_diplo, del_rate, diacritic_err, ins_rate, mer, mufi_err, region_cer, region_detection, wer`. — *preuves : `tests/evaluation/test_metrics_philology.py`, `…/test_registry.py`*. Reste : IoU polygonal exact (shapely, si consommateur) ; familles riches (NER/taxonomy) additives.
>
> **T8 (D-066)** : `RunResult` **v2** — `+ usage: tuple[DocumentUsage, ...]` (ressources par pipeline × document, triées, hors vues) ; `schema_version=2`, un JSON v1 sans `usage` se recharge. Le **contrat « analyses »** (canal unique typé pour le non-scalaire, 3 règles dures) est gravé dans la docstring de `result.py` ; le champ est **né en T9** avec `inference` (D-067). Preuves : `tests/evaluation/test_result.py::{test_usage_channel_round_trips,test_v1_payload_without_usage_still_loads}`.
>
> **T9 (D-067)** : `+ inference.py` (Nemenyi post-hoc + bootstrap percentile, stdlib pur, plancher partagé `MIN_SUPPORT`) `+ analysis.py` (canal E2 : `Analysis` + `InferencePayload`) ; le runner produit une analyse par (vue × métrique) applicable, sur les mêmes séries que `significance_p`. Parité numérique prouvée contre la source Picarones. Preuves : `tests/evaluation/test_inference.py` · `test_runner.py::test_inference_analyses_through_evaluate_run`.
>
> **T10 (D-068)** : `+ economics.py` + `pricing.json` (donnée datée packagée) — coût machine+jetons depuis les mesures E1, débit effectif, coût marginal, `pareto_front` ; payload `economics` = 2ᵉ membre de l'union `analyses` (discriminateur `kind` activé). Tests **dérivés à la main** (règle PLAN_PARITE §5.8b). Preuves : `tests/evaluation/test_economics.py`.
>
> **T11 (D-069)** : `+ metrics/diagnostics.py` (`searchability`, `hallucination` — registre = 12 métriques, vue `text` par défaut enrichie) `+ diagnostics.py` (collecteur branché au scoring : confusions, pires lignes, documents difficiles → 3ᵉ payload `analyses`). Preuves : `tests/evaluation/test_diagnostics.py`.
>
> **T12 (D-070)** : `+ calibration.py` — ECE/MCE (Guo 2017) + bins depuis les sidecars `CONFIDENCES` ; payload `calibration` = 4ᵉ membre de l'union. ECE/MCE en payload, pas en scalaire (la calibration qualifie, ne classe pas). Preuves : `tests/evaluation/test_calibration.py` (dérivés à la main).
>
> **T13 (D-071)** : `+ taxonomy.py` — 8 classes par règles pures (priorité segmentation→case→diacritic→ligature→visual→résiduel), 5ᵉ payload `analyses` ; classes à données externes élaguées (hapax/oov/abréviations). Preuves : `tests/evaluation/test_taxonomy.py`.
>
> **4g.1 (D-115)** : conformité HIPE (SPEC_HIPE) — profils `hipe`/`heritage` (couche 2, levier `non_word_to_space`) · `+ metrics/conformity.py` (**`cmer`** = MER caractère via `rapidfuzz.editops`, micro natif par `Observation(weight=H+S+D+I)`) · `+ conformity.py` (**post-passe cross-vues** : lit les résultats des vues raw/hipe/heritage déjà calculés — zéro re-scoring) → **7ᵉ payload `hipe`** (micro/macro §4.1 + `delta_norm`/`delta_heritage` + `n_missing` exposé) · section `conformity` (noms du scorer à la frontière ; `mer` ≡ wMER, pas de clé jumelle) · export JSONL via `artifact_sink` (`xerocr run --hipe-jsonl`, R-1.8 : sortie absente → `""` + warning) · glossaire `cmer` FR/EN. Oracle : parité **comptes jiwer** à chaque CI + golden vendoré skip-gaté (extra dédié `hipe-oracle`, Python ≥ 3.12). `[~]` réserves : fixture golden à vendorer · matérialisation R-1.8 dans les métriques → 4g.2. Preuves : `tests/formats/text/test_hipe_profiles.py` · `tests/evaluation/{test_metrics_conformity,test_conformity,test_hipe_golden}.py` · `tests/reports/test_conformity_section.py` · `tests/app/test_hipe_export.py`.
>
> **4g.2 (D-116)** : bilan de correction — `prepare_text` extrait vers `representations` (une seule définition « préparé comme au scoring ») · `+ correction.py` : analyse **par vue** des pipelines **2 étages** (une extraction GT/brut/corrigé) → **8ᵉ payload `correction`** : triplet de non-régression (égalités strictes) + `pref` + catastrophique (Δ > 0.10) · pcis §4.2 (clamp à q_brut nul, macro + médiane + \|pcis\|>1) · CCR/change_ratio/length_ratio + `overedited` · `char_ins_ratio` + `hallucination_heavy` · **absorption** multiset (ex-4e) · **sur-normalisation** positionnelle (ex-4c — tue le bug de clés fantômes C7 par construction) · éditions consécutives (R-2.6) · pires régressions ; seuils portés par le payload. **R-1.8 levée** : étage absent matérialisé vide + warning + `n_missing_*` (la réserve 4g.1). Section `correction`. Mono-étage → payload absent (≠ zéro muet). `[~]` réserve : **procédure `hallucination`** — machinerie complète, exécution sur runs réels avant 1.0 (critères a/b, SPEC §8). Preuves : `tests/evaluation/test_correction.py` (témoin entièrement dérivé à la main) · `tests/reports/test_correction_section.py`.
>
> **4a (D-117)** : données structurées — `+ metrics/structured_data.py` (détecteurs conservateurs : années 1000-2099, foliotation recto/verso **distincts**, montants, régnal — *roman* → 4b, helper `_roman_to_int` minimal absorbé à 4b) · scalaires **`numseq_strict`/`numseq_value`** (lentilles forme exacte / équivalence, multiset, `value ≥ strict`, adaptatifs `None` sans signal), registre = 15 métriques, **vue texte par défaut enrichie** · `+ structured_data.py` (collecteur, pattern taxonomy) → **9ᵉ payload `structured_data`** (pipeline × catégorie présente, formes perdues cap 12) · section `structured_data` · glossaire FR/EN. **`readability`/Flesch abandonné — acté** (D-117 ; couvert par 4g.2 + `hcpr`/`air`). Preuves : `tests/evaluation/{test_metrics_structured_data,test_structured_data}.py` (valeurs main : « fol. 3r »→« fol 3r » = valeur sans forme) · `tests/reports/test_structured_data_section.py`.
>
> **4b.1 (D-118)** : philologie/abréviations — `+ markers.py` (moteur containment+expansion **multiset**, réutilisable par famille ; table Capelli/MUFI **11 signes** en constante, `ñ` exclu, combinants NFC) ; `MarkerCollector` (pattern taxonomy) → **10ᵉ payload `philology`** (pipeline × famille × signe : strict/expansion). **Réparation R3** : développements en **mot entier** (`\b…\b`, toutes longueurs — `per` ≠ « permettre »). **Payload-only** (pas de scalaire registre : éviterait une colonne `None` sur corpus modernes ; la section adaptative est le consommateur). Section `philology` (nouvelle). `[~]` ouvert : familles early_modern (positionnel) / modern_archives (containment, table YAML si budget) / **roman 5 statuts (R1)** / **`air` (net-new HIPE) + `hcpr`** — sous-tranches suivantes. Expansion = borne optimiste documentée. Preuves : `tests/evaluation/test_markers.py` (R3 + multiset, valeurs main) · `tests/reports/test_philology_section.py`.

> **4b.2 (D-119)** : philologie/imprimé ancien — `markers.py` gagne une **stratégie `positional`** (déclarée par `MarkerFamily.strategy`) à côté de `containment` : un marqueur est *préservé* si toutes ses positions GT tombent dans un opcode `equal` de `Levenshtein.opcodes` (cohérent CER). Famille `EARLY_MODERN` (**5 catégories** : ligatures / long_s / dotless_i / ampersand / nasal_tildes — caractères vérifiés source), graphies **pré-composées** seules, **NFC** avant détection (décomposé voyelle+U+0303 → pré-composé, compté pareil) ; `ñ` **inclus** ici (≠ famille scribale D-118). `MarkerCollector` dispatche par stratégie ; **payload `philology` réutilisé sans rupture** (`n_strict == n_expansion == n_préservé`, un seul score — documenté). Section `philology` **étendue** : bloc positionnel (colonne « préservé » + libellés catégories) distinct du bloc containment. **Payload-only** (pas de scalaire registre — `early_modern_pres` afficherait `None` sur corpus modernes). **Pas de branche morte** (seules 2 stratégies utilisées) ; **pas de glossaire** (aucun scalaire affiché). `[~]` reste ouvert : modern_archives / **roman (R1)** / **`air`+`hcpr`**. Preuves : `tests/evaluation/test_markers.py` (positionnel sub/NFC/per-catégorie + mix de stratégies, valeurs main) · `tests/reports/test_philology_section.py` (bloc positionnel).

> **4b.3 (D-120)** : philologie/archives modernes — nouveau module **`archives.py`** : 9 catégories (~70 marqueurs : civilité/ordinaux/monnaies/administratif/état civil/ponctuation typo/latin moderne/biblio/adresse) en **constantes de module**, détection **regex bornée** (frontière après point — `M.` ≠ `M.A.`, `arr.` ≠ « arracher » ; `\b` pour l'alnum ; littéral pour l'Unicode) + **greedy plus-long-gagne** (`S.A.R.` avant `S.`). `markers.py` gagne une **3ᵉ stratégie `archival`** déléguant à `archives.py` ; famille `MODERN_ARCHIVES` (`markers` = clés d'affichage = catégories). **Containment MULTISET** (`Σ min(occ. GT, occ. hyp)`) — divergence **assumée** de la source (présence-par-occurrence qui n'enregistrait pas un `Mme`→`Mlle`), aligné sur 4b.1. Payload `philology` **réutilisé** (par catégorie : strict/expansion). Section étendue : bloc containment **par catégorie** (en-tête « catégorie » + libellés). **Module séparé** = isole le regex + tient le budget (markers 336 / archives 260 LOC, < 600). **Payload-only**, **pas de glossaire**, **pas de branche morte** (3 stratégies utilisées). `[~]` reste ouvert : **roman (R1)** / **`air`+`hcpr`**. Preuves : `tests/evaluation/test_archives.py` (frontières/multiset/greedy/ordinaux, valeurs main + end-to-end) · `tests/reports/test_philology_section.py` (bloc archives).

> **4b.4 (D-121)** : philologie/numéraux romains — nouveau module **`roman.py`** : parseur soustractif **validé** (rejette `IL`/`IIIII`/`VV`, accepte `IIII` médiéval), `j` final (`viij`→`viii`), détection greedy + **classification 5 statuts** (`strict_preserved`/`case_changed`/`j_dropped`/`converted_to_arabic`/`lost`). `RomanNumeralsCollector` (pattern taxonomy) → **11ᵉ payload `roman` dédié** (≠ `philology` : le 5-statuts ne se mappe pas sur strict/expansion). Section `philology` étendue (bloc romain). **R1 FERMÉE** : romain compté **une seule fois** (ici) ; `numseq` sans catégorie roman depuis D-117 ; **helper régnal absorbé** — `metrics/structured_data.py` importe `roman.roman_to_int` (source unique). **R2** : `min_length=2`. Scores strict/valeur **dérivés** des statuts (pas de double comptage). **Payload-only**, **pas de glossaire**. **Budget** : `analysis.py` → 636 LOC (hub union discriminée) → entrée `test_file_budgets` justifiée (731). `[~]` reste ouvert : **`air`+`hcpr`** (dernier de 4b). Preuves : `tests/evaluation/test_roman.py` (parseur/5 statuts/R1 single-count/R2, valeurs main + end-to-end) · `tests/reports/test_philology_section.py` (bloc romain).

**Enveloppe (plein-scope dès T1) :**
- [x] `RunResult` (`evaluation/result.py`) dimensionné plein-scope (scalaires texte/structure/NER/taxonomy + par-doc + `schema_version` ; clés stables ; `cross_engine` réservé). — *preuve : `test_result` (sérialisation déterministe) + `evaluate_run` le produit*
- [x] Registre **type-driven** unique (sélection par `input_types`) ; 0 ancien registre. — *preuve : `test_registry::test_get_and_select_by_input_types` + `test_no_forbidden_tokens` vert*
- [x] `DocContext` + runner (par-document → **agrégat micro** `Σerreurs/Σpoids` = la métrique au niveau corpus, `None`-exclu + support ; macro reconstructible depuis le détail par-doc). Les métriques renvoient `Observation(value, weight)` ; `weight` = dénominateur. — *preuve : `test_runner` (micro `1/6` ≠ macro `0.125` ; poids par-doc = 4 ; GT absente → `None`)* — **corrigé à l'audit T3** (était macro non pondéré + `safe_mean` supprimé).
- [x] `CrossEngineContext` + passe inter-moteurs (`cross_engine` écrit dans `RunResult`) ; **Wilcoxon/Friedman** avec **plancher de puissance** `_MIN_SUPPORT=6` (sous lui → `None`, pas un faux verdict) + filet `ValueError→None`. — *preuve : `test_metrics_stats` (significatif/égaux/sous-plancher) + `test_runner::test_cross_engine_significance_written`* — *(T2 ; durci à l'audit T3)*

**Garde-fous :**
- [x] `layer_dependencies` (`evaluation` → domain+formats ; `scipy` whitelisté) · `no_side_effect_imports` (décorateur **pur**, registre non auto-peuplé) · `file_budgets`. — *preuve : `test_evaluation_imports_are_allowed` + `test_fresh_registry_is_empty` + suite archi verte*
- [~] **`no-orphan métrique↔section`** : à la 1ʳᵉ section (couche 7, T1).

**Validation inter-couches :** voir `MIGRATION_PLAN.md` §3-T1 (1 CER → `RunResult` → HTML déterministe de bout en bout).

- [x] **WER/MER** (impl maison déterministe + **parité jiwer**, 15 cas) au socle texte. — *preuve : `test_metrics_text` (valeurs main) + `test_metrics_parity` (vs jiwer)*
- [x] **Profils de normalisation** (`normalization_profile`/`char_exclude`) honorés par le runner (couche 2 `formats/text`), symétriques GT/hyp ; **1 chargement par signature**. — *preuve : `test_runner` (caseless→0 ; profil inconnu→erreur) ; démo : vue `francais_medieval`*
- [x] **`cross_engine` + stats** : passe inter-moteurs (`CrossEngineContext`) → `RunResult.cross_engine` (clés `vue:métrique:test`) ; significativité **Wilcoxon/Friedman** (`scipy`). — *preuve : `test_metrics_stats` + `test_runner` (`text:cer:significance_p`)*
- [~] **Surface encore différée** : `compare` + sections engines/cross (T2.f) ; structure (T5) ; longitudinal/philologie/taxo/économie (T7).

---

*Référence : décisions actées en session de conception couche 3, réconciliées avec
`CLAUDE.md`. Enveloppe (contrats §3,§5-9) plein-scope maintenant ; surface remplie
par tranches (§15). Le reste émerge sous test (§13).*
