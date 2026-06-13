# ANALYSE Étape 4 — familles de métriques restantes (4a→4f)

> **Session d'ANALYSE** (CLAUDE.md §9) — aucun code produit. Guide de portage
> pour les tranches de construction de l'**Étape 4 de `PLAN_FIN_MIGRATION.md`**.
> - **Partie 1 (analyse source Picarones)** : **durable** — Picarones est gelé,
>   ces faits ne périment pas. Tout est **vérifié dans le code** (`fichier:ligne`,
>   chemins relatifs à `../Picarones/picarones/`).
> - **Partie 2 (cible XerOCR)** : **périssable**, chaque verdict est
>   **PROVISOIRE — à confirmer au build**. Le contact du code prévaut.
>
> Lu avant rédaction : `CLAUDE.md` (entier), `PLAN_FIN_MIGRATION.md` §Étape 4,
> `xerocr/evaluation/MIGRATION_COUCHE_3.md`, `MIGRATION_PLAN.md` (roll-up +
> D-066→D-093), code mergé (`result.py`, `analysis.py`, `metric.py`, `runner.py`,
> `metrics/*`, `reports/sections/*`, glossaire).
>
> **Amendé le 2026-06-11 (réconciliation HIPE — arbitrage « plan A »)** : la
> famille **4g — bilan de correction & conformité HIPE**
> ([`SPEC_HIPE.md`](../../SPEC_HIPE.md) v1.2) s'insère dans l'Étape 4 **avant la
> 1.0** ; `over_normalization` (4c) et `error_absorption` (4e) y sont déplacés ;
> `readability` (4a) est abandonné ; 4b gagne `hcpr`/`air` ; NER gagne la
> réparation R14. Détail : §0 (C9-C10), bloc « Arbitrages actés », §4g, §Ordre.
> `PLAN_FIN_MIGRATION.md` n'est pas modifié ici — réconciliation au 1ᵉʳ commit 4g
> (rituel roll-up + journal D-0xx).
>
> **Vérifié contre `main` post D-094→D-114 (même jour)** : aucune contradiction —
> `evaluation/metrics/` et `formats/text/` intacts, décisions UI/rapport
> orthogonales, pas de collision de `kind` (un 6ᵉ payload `document_texts` est
> arrivé, D-113). Renommage : **l'Étape 4 s'appelle désormais P2** (« ex-étape
> 4 », D-109 — parallélisable après P0, qui est livrée). Mises à jour induites :
> folds → strates (arbitrage n°7) ; **synergie P3** : le schéma GT du dataset
> curé (D-109) se conçoit en lisant CE guide (entités `.gt.entities.json` pour
> 4f, layout, strates, images pour 4d).

---

## 0. Corrections au plan — faits vérifiés qui contredisent une croyance écrite

À lire en premier : la table Étape 4 et le prompt de session portent quelques
croyances périmées ou imprécises. **Aucune ne renverse une décision actée**, mais
les tranches doivent travailler sur les faits ci-dessous, pas sur la légende.

| # | Croyance écrite | Fait vérifié | Preuve |
|---|---|---|---|
| C1 | 4e : « alignement ligne-à-ligne par `split('\n')` réputé fragile, à fiabiliser » | **Déjà fiabilisé à la source** (audit F15) : lignes alignées par `Levenshtein.opcodes` sur les listes de lignes AVANT le CER par ligne ; ligne GT supprimée → CER 1.0 ; lignes hyp en trop ignorées. Limite résiduelle : fusion/scission de lignes approximée (1 substitution + 1 délétion). | `metrics/line_metrics.py:191-205` |
| C2 | « `incremental_comparison.py` = raffinement change-point » (prompt de session) | **Faux** : c'est une **comparaison d'effet isolé par slot de pipeline** (type Latin square, pensée pour 180 pipelines = 5 OCR × 3 × 4 × 3). Aucun rapport avec le change-point. Absent de la table « Verdict métrique-par-métrique » du plan (ni gardé ni abandonné). | `metrics/incremental_comparison.py:1-30` |
| C3 | « `image_predictive` = stub sans implémentation » (PLAN_FIN_MIGRATION §Abandons #2) | **Pas un stub** : implémentation complète d'une pondération **éditoriale** (0.30·bruit + 0.30·(1−netteté) + 0.20·(1−contraste) + 0.20·|rot|/30) → « complexité paléographique » + « homogénéité corpus ». La docstring assume : « Pas de prédiction CER absolue ». **L'abandon reste justifié**, motif corrigé : aucune info nouvelle vs `image_quality` (simple re-pondération), nom mensonger, moitié « homogénéité » couplée au détecteur narratif `stratification_recommended` (supprimé). | `metrics/image_predictive.py:1-40` ; consommateurs : CLI `diagnose` (`interfaces/cli/_workflows.py:650`) + `reports/html/views/diagnostics.py:144-151` |
| C4 | 4c inclut `equivalence_profile` dans la famille unifiée | **Mort en production** : zéro consommateur hors tests (seules mentions = docstrings). Converge avec `MIGRATION_COUCHE_3.md` §11 qui le classait déjà « morts ». Sa fonction (CER sous équivalences choisies) est couverte côté XerOCR par les profils de normalisation couche 2 + preview YAML custom (D-089). → **abandon recommandé**, cf. §4c. | grep complet : seuls hits = docstring `lexical_modernization.py:56` + doc `metrics/__init__.py:35` |
| C5 | « roman compté deux fois » situé vaguement (le prompt suggérait `early_modern_typography`) | Le doublon est **`numerical_sequences` (catégorie `roman`, `min_length=2`) × `philological_hooks` (module `roman_numerals`, 5 statuts, `min_length=1` par défaut)**. `early_modern_typography.py` ne touche **pas** aux romains (zéro hit). Aggravant : les deux comptages utilisent des `min_length` **différents** → deux sections du même rapport peuvent donner des comptes différents pour le même texte. | `metrics/numerical_sequences.py:163` (`min_length=2`) ; `metrics/philological_hooks.py:94` (appel sans `min_length` → défaut 1, `roman_numerals.py:322`) |
| C6 | — (non documenté au plan) | **Bug de clés fantômes #1 (NER)** : l'agrégateur écrit `total_hallucinated`/`total_missed`, le renderer lit `hallucinated_total`/`missed_total` → zéros affichés en silence ; le test du renderer fixture les clés fantômes (couverture mensongère). | `app/services/_benchmark_ner.py:180-181` vs `reports/html/renderers/ner.py:92-93` |
| C7 | — (non documenté au plan) | **Bug de clés fantômes #2 (over_normalization)** : le hook produit `{score, total_correct_ocr_words, over_normalized_count}`, le renderer lit `{modernization_rate, preserved_archaic_count, lost_archaic_count}` → la vue rend des zéros. | `metrics/over_normalization.py:76-82` vs `reports/html/renderers/over_normalization.py:69,85-86` |
| C8 | 4d : « `robustness.py` à la racine d'`evaluation/` » | Vit en réalité dans `metrics/robustness.py` (581 LOC). Le re-OCR n'importe **pas** d'adapter : moteur **injecté** par duck typing (`OCREngine = Any`), déclenché par la CLI dédiée `picarones robustness`. | `metrics/robustness.py:40,340-376` ; `interfaces/cli/_robustness.py:23-191` |
| C9 *(2026-06-11)* | v1 de ce guide : « le matching NER est solide » | L'algorithme d'appariement est correct en interne, mais l'IoU compare des spans de **deux systèmes de coordonnées différents** : entités or = offsets sur le texte **GT**, entités hypothèse = offsets sur le texte **OCR** (`entity_extractor(dr.hypothesis)`), et `ner.py` n'utilise jamais le champ `text` pour apparier. Toute insertion/délétion amont décale les offsets aval → une entité **parfaitement transcrite** est comptée « manquée + hallucinée » dès que le drift dépasse sa longueur. Le F1 mesure en partie le profil ins/del du moteur, pas la préservation des entités. → réparation **R14** (4f). | `app/services/_benchmark_ner.py:92-97` ; `evaluation/metrics/ner.py:122-175` |
| C10 *(2026-06-11)* | docstring source : searchability suit « la convention Elastic `fuzziness: AUTO` » | Le code applique distance ≤ 2 **uniforme à toutes les longueurs** (l'AUTO d'Elastic réserve 2 aux mots ≥ 6 : 0 si < 3, 1 si 3-5) — XerOCR a hérité du 2 plat (`_SEARCH_MAX_DISTANCE = 2`) + appariement glouton « premier non utilisé ». Effet plafond sur les mots courts (≤ 4 caractères : quasi toujours « retrouvables ») → différences entre moteurs écrasées. Durcissement **pré-1.0** acté (SPEC_HIPE §10). | `xerocr/evaluation/metrics/diagnostics.py:26,45-61` |

> **Leçon transverse C6/C7** : les deux bugs « clés fantômes » sont
> l'impossibilité structurelle que XerOCR élimine **par construction** — payloads
> Pydantic `frozen, extra="forbid"` typés, sections qui lisent les **champs** du
> payload (pas des clés de dict). C'est l'argument de fond du canal `analyses`.

---

# PARTIE 1 — ANALYSE SOURCE PICARONES (durable)

## Mécanique d'enregistrement commune (contexte pour toutes les familles)

Picarones empile 3 mécanismes (la « fragmentation » dénoncée par le plan) :

1. **Registre typé** `@register_metric(name=…)` (`metric_registry`) — scalaires
   par jonction `(TEXT, TEXT)` / `(ENTITIES, ENTITIES)`.
2. **Hooks runner** `@register_document_metric(attribute=…)` /
   `@register_corpus_aggregator(attribute=…)` (`metric_hooks`, câblés dans
   `metrics/builtin_hooks.py`) — résultats **dict** posés comme attributs de
   `DocumentResult` / `EngineReport`, activés par profils
   (`_STANDARD_PROFILES = standard, philological, diagnostics, full`).
3. **Appel direct hors runner** — la couche `reports/html/{data,views,renderers}`
   ou la CLI calcule elle-même (rare_tokens, inter_engine, worst_lines,
   longitudinal, robustness…). C'est l'anti-pattern « data-layer qui ré-agrège »
   (CLAUDE.md §8.3).

XerOCR remplace tout par : **scalaires** = `DocumentMetric` (`Observation`) dans
le registre type-driven ; **non-scalaire** = collecteur/fonction d'analyse →
payload `RunResult.analyses` ; **rapport** = section qui lit. Aucun hook.

---

## 4a — Données structurées & lisibilité

### Fichiers et verdicts

| Fichier (LOC) | Rôle vérifié | Verdict (PROVISOIRE — à confirmer au build) |
|---|---|---|
| `metrics/numerical_sequences.py` (424) | Détecte 5 catégories de séquences en GT et vérifie leur restitution : années arabes, romains (délégué), foliotation, montants, années régnales. 2 scores par catégorie + globaux : **strict** (forme exacte) / **value** (équivalent numérique). | **GARDER** — 🔶 retirer la catégorie `roman` (résolution doublon C5, propriété transférée à 4b) ; le régnal continue d'utiliser `roman_to_int` comme **helper** (pas un comptage). |
| `metrics/numerical_sequences_hooks.py` (102) | Adaptatif (GT sans séquence → `None`) + agrégateur corpus (recalcule les scores micro, cap `lost_items` à 50/catégorie). | **SUPPRIMER** (plomberie hooks) — la logique adaptative/micro passe dans la métrique + le payload XerOCR. |
| `metrics/readability.py` (252) | Flesch [0,100] borné + **delta** GT↔hyp ; syllabes = groupes de voyelles consécutives (`aeiouyàâäéèêëîïôöùûüÿæœ`), mot sans voyelle = 1 ; phrases = split `[.!?…]`, min 1. | **NE PAS PORTER** — arbitré 2026-06-11 (cf. §Abandons) : construct hors domaine de validité sur de l'OCR à ponctuation abîmée (le compte de phrases s'effondre → deltas parasites) ; ce qu'il détecte est mesuré directement par `lexical_modernization`/4g.2/`hcpr`-`air`. L'analyse des formules ci-dessous reste documentée (durable). |
| `metrics/readability_hooks.py` (114) | Adaptatif (≥ 5 mots GT, `_MIN_WORDS_FOR_FLESCH = 5`) ; agrégat mean/median/min/max + comptage over/under-normalisés au seuil **±5**. | **SUPPRIMER** (plomberie) — seuils ±5 et minimum 5 mots repris dans la cible. |
| `metrics/roman_numerals.py` (480) | Parser/validateur romain complet : normalisation casse + `j` médiéval final (`ij`→`II`), parsing soustractif strict, rejet des formes absurdes (`IIIII`, `VV`, paires soustractives illégales) ; détection regex `\b[IVXLCDMivxlcdmj]+\b` + validation ; classification en **5 statuts** (`strict_preserved`, `case_changed`, `j_dropped`, `converted_to_arabic`, `lost` ; `VALUE_PRESERVING = les 4 premiers`). 480 LOC justifiées (validation anti-faux-positifs + j médiéval). | **GARDER** (le parser) — **propriété transférée à la famille 4b** (un seul comptage). |

### Formules & constantes décisives (vérifiées)

- **Années arabes** : `\b(1[0-9]{3}|20[0-9]{2})\b` (bornes 1000–2099, frontière de mot).
- **Foliotation** : `\b(?:fol\.?|f\.|pp\.|p\.|n\.°|n°)\s*(\d+(?:\s*-\s*\d+)?)\s*([rvRV])?` ;
  clé normalisée `{nums}{r|v}` — **r/v non interchangeables** (recto/verso).
- **Montants** : nombres + unité dans `livres?|sols?|deniers?|écus?|florins?|francs?|l\.|s\.|d\.|£|€|₣`
  (insensible casse), unité canonisée par table interne.
- **Régnal** : `\b(?:l['']\s*)?an\s+(?:de\s+(?:grâce|la\s+R[eé]publique)\s+)?([IVXLCDMivxlcdm]+|\d{1,4})\b` ;
  valeur via `roman_to_int` ou `int`.
- **Scores** : `strict_score = n_strict/n_total`, `value_score = n_value/n_total`
  ∈ [0,1] ; **`None` si `n_total == 0`** (« Classe B » — document non applicable,
  exclu de l'agrégat, jamais un 0 silencieux).
- **Flesch** (`readability.py:64-67`) :
  `score = clamp(base − k_mots·(W/P) − k_syll·(S/W), 0, 100)` avec
  **FR = (207.0, 1.015, 73.6)** (Kandel-Moles 1958) et
  **EN = (206.835, 1.015, 84.6)** (Flesch 1948).
  `flesch_delta = score(hyp) − score(ref)` ∈ [−100, +100].
  Lecture : Δ > +5 = sur-normalisation (lissage LLM) ; Δ < −5 = dégradation OCR.

### Enregistrement & consommateurs (hors tests)

- Scalaires registre : `numerical_sequence_strict_score`/`_value_score`
  (`numerical_sequences.py:389-416`), `flesch_delta_fr`/`_en`
  (`readability.py:215-242`), `roman_numeral_strict_score`/`_value_score`
  (`roman_numerals.py:432-462`).
- Hooks : `builtin_hooks.py:265-283` (doc) + `:564-587` (corpus), attributs
  `numerical_sequence_metrics`/`aggregated_numerical_sequences`,
  `readability_metrics`/`aggregated_readability`.
- Renderers : `reports/html/renderers/numerical_sequences.py` (table moteur ×
  5 catégories, intégrée à la vue diagnostics composite
  `engines_diagnostics.py:130-137`) ; `renderers/readability.py` — **legacy
  seulement** (template `view_analyses.html`, hors vue composite) ;
  `renderers/philological.py:473-544` (section romaine 5 statuts).
- Aucun export CSV/CLI dédié.

### Bugs/silences/fragilités source

- Doublon roman + `min_length` divergent (C5).
- Faux positifs assumés : formes verbales rares non couvertes (« mil cinq
  cens ») ; regex volontairement conservatrices (c'est le bon biais : la
  précision prime sur le rappel pour une métrique de restitution).
- Aucun non-déterminisme. Divisions par zéro protégées partout.

---

## 4b — Philologie étendue

### Fichiers et verdicts

| Fichier (LOC) | Rôle vérifié | Verdict (PROVISOIRE) |
|---|---|---|
| `metrics/abbreviations.py` (352) | Abréviations scribales médiévales (Capelli/MUFI) : table de **12 signes** → expansions (`ꝑ→per/par`, `ꝓ→pro`, `ꝗ→qui`, `ꝙ→quia`, `ꝯ→us/con`, `⁊→et`, `ꝝ→rum`, `ꝫ→et`, `ꝭ→is`, `p̃→par/per`, `q̃→que/qui`, `ñ→an/en`). Détection NFD (lettre + U+0303 ou caractère dédié). 2 scores : **strict** (forme abrégée présente verbatim) / **expansion** (abrégée OU développée). | **GARDER** — 🔶 table → donnée (YAML package-data) ; durcir la recherche d'expansion (frontière de mot seulement si ≤ 2 lettres → `per` matche dans « permettre », imprécision documentée à corriger). |
| `metrics/early_modern_typography.py` (345) | Marqueurs typographiques de l'imprimé ancien, **5 catégories** : `ligatures` (ﬀﬁﬂﬃﬄﬅﬆ), `long_s` (ſ), `dotless_i` (ı), `ampersand` (&), `nasal_tildes` (ãñõũẽĩ + décomposés). **Sémantique positionnelle** : marqueur « préservé » si toutes ses positions GT tombent dans un opcode `equal` de `Levenshtein.opcodes(ref, hyp)` (cohérent CER, audit F4/F14). | **GARDER** — tables → donnée ; conserver la sémantique positionnelle (≠ containment). |
| `metrics/modern_archives.py` (601) | Abréviations/marqueurs des archives XIXᵉ-XXᵉ : **9 catégories, ~73 entrées** (civilités `Mme/Mgr/S.A.R.…`, ordinaux exposants `1ᵉʳ/XIXᵉ…`, monnaies `₶/₣/ƒ/£/l./s./d.`, administratif `arr./dép.…`, état civil `°/†/✶/⚭/ép./vve`, ponctuation typographique `«»—–…''`, latin moderne `e.g./i.e./etc./cf./ibid.…`, bibliographique `vol./t./p./n°/r°/v°…`, adresse `bd/av./r.…`). Frontières regex différenciées (alphabétique vs point final vs Unicode pur, `:268-269`), greedy « plus long gagne » sans chevauchement. Scores strict/expansion par catégorie + globaux. | **GARDER** — 🔶 **les 9 tables (≈ 60 % du fichier) sortent en donnée YAML** (résout le budget : 601 LOC → moteur ≈ 200) ; sémantique containment strict/expansion conservée. |
| `metrics/philological_hooks.py` (363) | Orchestrateur « adaptatif » des **6 modules** philologiques (`unicode_blocks`, `abbreviations`, `mufi`, `early_modern`, `modern_archives`, `roman_numerals`) : calcule chacun, ne retient que ceux dont la GT porte du signal (`n_*_reference > 0`), agrège par module au corpus. ⚠️ `try/except Exception` par module (warning puis continue, `:122-128`). | **SUPPRIMER** (plomberie hooks) — l'adaptativité (`None` sans signal) passe dans chaque métrique ; l'agrégation dans le collecteur/payload. NB : `unicode_blocks` et `mufi` sont **déjà couverts** côté XerOCR (`mufi_err`, `diacritic_err`, `cer_diplo`) — ne pas re-porter. |

### Formules (pattern commun vérifié)

```
strict_score    = n_strict_preserved    / n_total_in_reference   ∈ [0,1] ; None si n_total = 0
expansion_score = n_expansion_preserved / n_total_in_reference   (strict OU développé)
préservation positionnelle (early_modern) : positions GT ⊆ opcodes "equal"
agrégat corpus = micro (Σ numérateurs / Σ dénominateurs), pas moyenne de taux
```

Deux **sémantiques de préservation distinctes à conserver telles quelles** :
- *positionnelle* (early_modern) — le caractère doit être à sa place ;
- *containment* (abbreviations, modern_archives) — la forme (ou son expansion)
  existe quelque part dans l'hypothèse (insensible casse pour les expansions).

### Le doublon roman, précisément (réparation 🔶 centrale)

- Comptage 1 : `numerical_sequences._detect_romans_with_values` →
  `detect_roman_numerals(text, min_length=2)` ; lentille **valeur** (strict/value),
  affiché dans la table « séquences numériques ».
- Comptage 2 : `philological_hooks` → `compute_roman_numeral_metrics(ref, hyp)`
  (défaut `min_length=1`) ; lentille **restitution** (5 statuts), affiché dans la
  section philologique.
- Conséquences : même entité comptée deux fois, **avec des assiettes différentes**
  (un `I` isolé compte côté philologique, pas côté séquences) ; deux renderers.
- Perte si on n'en garde qu'un : la lentille 5 statuts **subsume** strict/value
  (`strict = strict_preserved` ; `value = n_total − lost`) — **rien n'est perdu
  en gardant la lentille philologique seule** et en dérivant les deux scores.

---

## 4c — Fidélité textuelle

### Fichiers et verdicts

| Fichier (LOC) | Rôle vérifié | Verdict (PROVISOIRE) |
|---|---|---|
| `metrics/rare_tokens.py` (257) | Rappel des **tokens rares du corpus** (fréquence GT ≤ `max_freq=2` : hapax + dis legomena) ; tokenisation `\w+(?:[''\-]\w+)*` ; comptage **multiset** (`recall = Σ min(count_ref, count_hyp) / Σ count_ref` sur les rares) ; `None` si aucun rare. **ORPHELIN du runner** : calculé en couche reports (`reports/html/data/extra_metrics.py:50-102`) avec pré-passe fréquences faite là-bas — il n'y a **pas** de mécanique de pré-passe dans le runner Picarones (la note `MIGRATION_COUCHE_3.md` §13 « pré-passe stats corpus → DocContext » décrit la cible, pas la source). | **GARDER** (le calcul) — 🔶 rapatrier en couche 3 via **collecteur** (cf. Partie 2). |
| `metrics/lexical_modernization.py` (263) | Table de **modernisation lexicale par token GT** : alignement mot-à-mot `difflib.SequenceMatcher(autojunk=False)`, tags equal/replace/delete (replace apparié 1-à-1, délétion → variante `"∅"`) ; par token : `n_total`, `n_modernized`, `rate_modernized`, `variants{hyp: count}` ; `top_modernized_tokens` pour le tri. **ORPHELIN** : pas de hook ; consommé par la vue optionnelle `advanced_taxonomy` + le registre `levers` (tous deux non portés). | **GARDER** (le calcul, diagnostic précieux pour les pipelines LLM) — 🔶 même collecteur que rare_tokens. |
| `metrics/over_normalization.py` (235) | **Pipelines OCR→LLM uniquement** : aligne OCR→GT et LLM→GT (`rapidfuzz.Levenshtein.opcodes`, audit F18) ; pour chaque mot GT **correct côté OCR**, si le LLM l'a changé → sur-normalisé. `score = over_normalized / total_correct_ocr_words` ∈ [0,1] ; passages exemples capés à 20. Enregistré agrégateur corpus (`builtin_hooks.py:211-215`), alimenté par le runner via `pipeline_metadata` (`app/services/_benchmark_helpers.py:113-127`). **Bug C7** : renderer lit des clés fantômes. | **GARDER** — 🔶 réparer C7 par construction (payload typé) ; nécessite l'accès aux **deux étages** (RAW_TEXT et CORRECTED_TEXT). |
| `metrics/equivalence_profile.py` (199) | Catalogue de **15 règles d'équivalence nommées** (ſ→s, u=v, i=j, æ, œ, þ→th, ð→th, ȝ→y, &→et, ỹ→yn, ꝑ→per, ꝓ→pro, ꝗ→que, y=i, vv→w) + `apply_selected_equivalences` (remplacements séquentiels, ordre = ordre catalogue) + `compute_cer_with_equivalences`. **MORT** (C4). | **SUPPRIMER / NE PAS PORTER** — divergence assumée avec la table 4c (cf. §Abandons). La fonctionnalité = profil de normalisation custom, déjà couverte (couche 2 + D-089). |
| `metrics/searchability_hooks.py` (81) | Wrapper hook de `searchability.py` (Levenshtein ≤ 2, multiset). | **SUPPRIMER** — `searchability` est **déjà livré** dans XerOCR (T11). Seule différence : la source expose aussi `missed_tokens` (liste) — sans consommateur prévu côté XerOCR, ne pas porter (« pas de consommateur = supprimé »). |

### La « fragmentation » 4c, factuellement

| Module | Enregistrement source | Calculé par | Rendu |
|---|---|---|---|
| rare_tokens | aucun | couche reports (`extra_metrics.py`) | renderer dédié |
| lexical_modernization | aucun | tests/synthetic + vue optionnelle | renderer dédié |
| over_normalization | agrégateur corpus | runner (helpers `_benchmark_*`) | renderer **cassé** (C7) |
| equivalence_profile | aucun | personne | aucun |
| searchability | registre + hook (double chemin) | runner | renderer dédié |

Cinq modules, cinq câblages différents, un bug d'affichage, un mort — c'est le
🔶 « câblage homogène » du plan.

---

## 4d — Robustesse & qualité image

### Fichiers et verdicts

| Fichier (LOC) | Rôle vérifié | Verdict (PROVISOIRE) |
|---|---|---|
| `metrics/robustness.py` (581) | Courbes CER vs niveaux de dégradation **réels** (re-OCR). Dégradations PIL (`degrade_image_bytes`) : **noise** σ∈[0,5,15,30,50,80] (gaussien par pixel, **`random.Random(0)` — seed fixe**, `:128`), **blur** r∈[0,1,2,3,5,8] (GaussianBlur), **rotation** ∈[0,1,2,5,10,20]° (`rotate(-level, expand=False, fillcolor=(245,240,232))`), **resolution** ∈[1.0,0.75,0.5,0.33,0.25,0.1] (NEAREST down+up), **binarization** seuils [0=Otsu,64,96,128,160,192]. `RobustnessAnalyzer(engines, cer_threshold=0.20).analyze(corpus, max_docs=10)` → `DegradationCurve{levels, labels, cer_values, critical_threshold_level}` ; niveau critique = premier niveau où CER > 0.20. Moteur **injecté** (duck typing `OCREngine = Any`, `:40`) — pas d'import adapters. Coût défaut : 10 docs × 6 niveaux × 5 types = **300 appels moteur**. Déclenchement : CLI dédiée `picarones robustness` (`--max-docs`, `--cer-threshold`, `--degradations`, `--demo`). | **GARDER** — 🔶 exécution re-OCR **hors couche 3** (orchestrateur), opt-in + bornée (déjà le cas à la source : CLI séparée + `max_docs`) ; dégradations pures + assemblage de courbes restent couche 3. |
| `metrics/robustness_projection.py` (287) | Projette les courbes synthétiques sur la qualité **mesurée** des images du corpus : interpolation **linéaire** entre niveaux (`:111`), mapping qualité→niveau par défaut (`noise→noise_level`, `blur→blur_score`, `rotation→rotation_angle`, `resolution→resolution_score`), déficit attendu = `expected_mean − baseline`. **Assume l'indépendance des dégradations** (note `:254-256`). | **SUPPRIMER / NE PAS PORTER** — absent de la ligne 4d du plan et de la table des gardées ; science faible (interpolation linéaire de courbes synthétiques × hypothèse d'indépendance) ; cf. §Abandons. |
| `metrics/image_quality.py` (408) | Mesures réelles par image : **netteté** = `min(1, variance_laplacien_3×3 / 500.0)` (`:161`) ; **bruit** = `min(1, MAD_gradients / 30.0)` (`:261`) ; **rotation** estimée par projections horizontales ±5°, pas 1° (NumPy seul) ; **contraste** Michelson sur percentiles 5/95. Composite : `quality = 0.40·netteté + 0.30·contraste + 0.20·(1−bruit) + 0.10·max(0, 1−|rot|/10)` (`:329-332`). Tiers : good ≥ 0.7. Double chemin NumPy+PIL → PIL seul → `error` champ (image illisible exclue proprement). Constantes **empiriques non sourcées** (500, 30, poids). | **GARDER** — 🔶 documenter chaque constante comme convention éditoriale (valeur + lecture) dans la docstring ; pas de fallback « mock » (le `generate_mock_quality_scores` sert la démo Picarones, ne pas porter). |
| `metrics/image_predictive.py` (283) | Cf. **C3** : combinaison pondérée des features d'`image_quality` (« complexité paléographique ») + hétérogénéité inter-docs (« homogénéité »). | **SUPPRIMER / NE PAS PORTER** — abandon confirmé (motif corrigé en C3). |

Déterminisme source : bruit seedé `Random(0)`, démo seedée 42, mock seedé
`hash(doc_id)` — rien à réparer, tout à **préserver**.

---

## 4e — Inter-moteurs & lignes

### Fichiers et verdicts

| Fichier (LOC) | Rôle vérifié | Verdict (PROVISOIRE) |
|---|---|---|
| `metrics/inter_engine.py` (484) | (1) **Divergence taxonomique** entre moteurs : JS-divergence en **bits** (`log2`), lissage ε=1e-12, `M=(P+Q)/2`, clampée [0,1] (`:100-113`), sur les **distributions de classes d'erreurs** (taxonomy) ; matrice paire-à-paire + `max_pair`. (2) **Complémentarité** : `oracle_token_recall` **multiset bag-of-words** = `Σ_token max_moteur(min(count_GT, count_hyp)) / Σ count_GT` (`:195-210`) — borne **supérieure optimiste** documentée (ignore l'ordre) ; `complementarity_gap` = `{oracle_recall, best_single_recall, best_engine, absolute_gap, relative_gap = abs_gap / max(1−best, 1e-12)}` ; `per_doc` capé à 50. ⚠️ conventions : GT vide → recall **1.0** (`:201`) ; distributions non validées (somme ≈ 1 supposée). Pas de hook : appelé par le renderer + le détecteur narratif `ensemble_opportunity` (supprimé). | **GARDER** — 🔶 GT vide → `None` (pas 1.0) ; réutiliser les comptages taxonomy **déjà collectés** par XerOCR (zéro recalcul). |
| `metrics/error_absorption.py` (276) | Gain net d'une jonction OCR→LLM, **multiset** : `_missing_tokens(ref, hyp) = Counter(ref) − Counter(hyp)` par token ; corrigées = `max(0, manquants_avant − manquants_après)`, introduites = inverse, conservées = min ; `correction_rate = n_corrected/n_errors_before` (None si 0), `introduction_rate` idem, `net_improvement = n_corrected − n_introduced` (peut être < 0) ; échantillons de tokens capés à 50 ; `case_sensitive=False` par défaut (⚠️ masque les erreurs de casse). Pas de hook (renderer + vue pipeline). | **GARDER** — 🔶 partage l'extraction « deux étages » avec `over_normalization` (4c) ; trancher la casse via la normalisation de la vue (pas un flag interne). |
| `metrics/line_metrics.py` (305) | Distribution du CER **par ligne** : alignement **fiabilisé** (C1) ; percentiles p50/p75/p90/p95/p99 (interpolation linéaire) ; **Gini** `G = (2·Σ(i+1)·xᵢ)/(n·Σxᵢ) − (n+1)/n` ∈ [0,1] ; `catastrophic_rate` par seuils **défaut [0.30, 0.50, 1.00]** (`:171-172`) ; heatmap positionnelle 10 bins ; CER ligne plafonné à 1.0. Hook doc+corpus (`builtin_hooks.py:191-199, 401-417`). | **GARDER** — porter l'alignement F15 **tel quel** (il est la version fiable) ; documenter la limite fusion/scission. |
| `metrics/worst_lines.py` (199) | Top-N transversal des pires lignes (re-split des textes du `BenchmarkResult`, fragile après `compact()`). | **SUPPRIMER / NE PAS PORTER** — **déjà couvert** par XerOCR (`DiagnosticsPayload.worst_lines`, T11/D-069, collecté au fil du scoring avec extraits verbatim — design supérieur). |
| `metrics/longitudinal.py` (373) | Sur l'historique : (1) **tendance OLS** (pente/intercept/R² sur CER vs temps ordinal-jours ; `R²=1.0` si tous CER égaux — convention contre-intuitive documentée) ; (2) **« change-point »** = balayage de l'index maximisant `|mean_after − mean_before|` avec `min_segment_size=3` (`:221-233`) — **pas un CUSUM ni un vrai Pettitt** (aucune statistique de test, aucune p-value : le max-diff « détecte » toujours quelque chose, seul un seuil Δ ≥ 0.01 filtre). Parsing timestamps multi-formats, silencieux si invalide. | **GARDER** (OLS) — 🔶 remplacer le max-diff par un **vrai test de rupture** (cf. Partie 2). |
| `metrics/incremental_comparison.py` (253) | Cf. **C2** : effet isolé d'un slot (groupes à slots fixes, rangs moyens ex-aequo partagés, best/worst par moyenne). Consommé par la vue pipeline. | **SUPPRIMER / NE PAS PORTER** — hors liste des gardées ; exige des métadonnées « slots » que l'enveloppe XerOCR ne porte pas (pipeline = nom) ; cas d'usage 180-pipelines inexistant. Cf. §Abandons. |

---

## 4f — NER

### Fichiers et verdicts

| Fichier (LOC) | Rôle vérifié | Verdict (PROVISOIRE) |
|---|---|---|
| `metrics/ner.py` (309) | **Calcul pur, zéro dépendance** : `Entity(label, start, end, text)` (offsets caractères sur le texte GT niveau TEXT ; `text` informatif, jamais utilisé pour matcher). **Appariement** : IoU de spans = `inter/union` (`:122-130`) ; labels comparés **casefold** (`:153`) ; **greedy déterministe** trié `(−score, ref_idx, hyp_idx)`, chaque entité appariée une fois ; seuil **IoU ≥ 0.5** (défaut, `:203`). P/R/F1 protégés div-0 ; **global = micro** (TP/FP/FN agrégés), **par catégorie** = même formule sur les compteurs de la catégorie. Manquées = GT non appariées (FN listées) ; hallucinées = hyp non appariées (FP listées). Scalaire `ner_f1` enregistré jonction `(ENTITIES, ENTITIES)`. | **MODIFIER** 🔶 — algorithme d'appariement sain, mais **défaut de validité C9** : IoU sur des offsets de deux textes différents (GT vs hypothèse) → invalide dès que l'amont insère/supprime. Réparation **R14** obligatoire au portage. |
| `metrics/ner_backends.py` (227) | `SpacyEntityExtractor(model_name="fr_core_news_sm")` : lazy-load idempotent ; **spaCy absent → warning + désactivé ; modèle absent (OSError) → warning + désactivé ; `__call__` → `[]`** (`:140-176`) — le benchmark continue avec des hypothèses vides → **scores faux (recall 0) sans message utilisateur** : LE silence à tuer. Profils : `fr/fr_lg/en/en_lg/multilingual=xx_ent_wiki_sm/hipe`. **Version du modèle spaCy non tracée** (reproductibilité cassée). Protocol `EntityExtractor` (extensible). | **DÉPLACER → `adapters/ner/`** (spaCy = SDK, hors whitelist effective couche 3) — 🔶 fail-closed + version tracée (cf. Partie 2). |

**Vérité-terrain** (`evaluation/corpus.py`) : sidecar **`.gt.entities.json`**
(`GT_SUFFIXES[ENTITIES]`, `:187-191`), format `{"entities": [...]}` **ou** liste
nue ; entité = `{"label", "start", "end", "text"?}` (offsets caractères) ; format
invalide → warning + skip.

**Découplage source** : la NER ne passe **pas** par le pipeline — c'est un
post-traitement `attach_ner_metrics_to_benchmark` déclenché si
`--entity-extractor DOTTED_PATH` (CLI seulement, jamais exposé au web), qui mute
le `BenchmarkResult` après coup. Plus le bug C6 (clés fantômes) et le test
circulaire du renderer.

---

# PARTIE 2 — RÉORGANISATION CIBLE XerOCR (périssable, PROVISOIRE — à confirmer au build)

## Arbitrages actés (2026-06-11 — « plan A », SPEC_HIPE v1.2)

1. **Plan A** : la famille **4g** (conformité HIPE + bilan de correction) livre
   **avant la 1.0**, intégrée à l'Étape 4 — la 1.0 revendique la conformité.
2. **Architecture 4g** : implémentation **in-tree** ; `hipe-ocrepair-scorer`
   épinglé en **dépendance de test** (oracle golden 1e-9, job CI 3.12) — jamais en
   runtime (Python ≥ 3.12 vs matrice 3.11, `np.random.seed` global, validation
   circulaire). Pattern maison déjà amorti (jiwer = oracle de parité, `text.py:8-9`).
3. **`readability`/Flesch : abandonné** (retiré de 4a — cf. §Abandons).
4. **`searchability` : durci avant 1.0** — échelle Elastic AUTO (0 édition < 3
   caractères · 1 pour 3-5 · 2 pour ≥ 6) ; les valeurs baisseront vs runs passés,
   raison de plus pour le faire pré-gel.
5. **`hallucination` : décision différée-avec-critères, exécutée à 4g.2** (avant
   1.0) : sur 2-3 runs réels (OCR seul · OCR+LLM modernisant · zero-shot),
   (a) le trigramme flagge-t-il un document que (`char_ins_ratio` + part
   d'éditions groupées) ne flagge pas ? (b) faux positifs sur GT diplomatique +
   LLM modernisant ? Aucun signal unique → retrait de la clé ; sinon conservation
   avec caveat documenté.
6. **Liste `C` (hcpr/air) : une seule liste, archaïque uniquement** — accents
   modernes exclus (perte = `diacritic_err`, vérifié `diacritics.py:50-58` ;
   deux directions visibles en classe taxonomy `diacritic`). **Q4 actée
   (2026-06-11)** : défaut = **`archaic_core`** trans-langue
   (`ſ ꝛ ⁊ ꝑ ꝓ ꝗ ꝙ ꝯ ꝝ ꝫ ꝭ þ ð ȝ` + `aͤ oͤ uͤ`) ; **œ æ ß ç exclus du défaut**
   (langue-relatifs — « cœur » est du français moderne → faux positifs `air`) ;
   **`air` actif par défaut**, **`hcpr` visible seulement avec liste configurée**
   (anti-colonne-jumelle de `mufi_err`) ; listes nommées en package-data +
   override par run, nom + hash au manifeste et au rapport.
7. **Différés d'enveloppe** *(amendé post-P0, D-110/D-111)* : la stabilité
   inter-répliques (R-2.7) **reste différée** (aucune notion de réplique dans
   `RunResult`). Les **folds (R-2.4)**, eux, ont désormais leur canal :
   `DocumentRef.metadata["stratum"]` → `RunDocumentResult.stratum` (P0) — les
   folds HIPE se mappent sur les **strates** ; ne reste différée que la
   mécanique d'agrégation/pondération par strate (consommateur « CER par
   strate » prévu par D-109), à réévaluer à sa tranche.

## Rappel des coutures d'enveloppe disponibles (rien à modifier, tout existe)

| Besoin d'une famille | Couture existante (mergée) |
|---|---|
| Scalaire par-document | `DocumentMetric` + `Observation(value, weight)` ; `None` = N/A ; micro-agrégat automatique (`runner._aggregate`) |
| Non-scalaire | payload Pydantic `frozen, extra="forbid"` dans `analysis.py`, membre de l'union `AnalysisPayload` (discriminée `kind`) + `Analysis(scope, view, …)` |
| Collecte au fil du scoring (zéro relecture) | pattern `DiagnosticsCollector`/`TaxonomyCollector` : `observe(pipeline, ref, hyp)` pendant la passe 1, `build(view)` après (`runner.py:90-149`) |
| Accès aux **deux étages** d'un pipeline (RAW_TEXT *et* CORRECTED_TEXT) | pattern `calibration_analysis(view, corpus, pipeline_outputs)` : fonction d'analyse qui lit `pipeline_outputs` directement (`runner.py:144-146`) |
| Nouveau type d'artefact GT | `ArtifactType.ENTITIES` existe (`domain/artifacts.py:66`) ; loader à étendre dans `representations.load_representation` |
| Version d'un module externe | `RunManifest.module_versions` (T6) — un Module déclare sa version |
| Section de rapport | `Protocol Section` (`render(RunResult, ctx) → Html|None`), modèle = `sections/taxonomy.py` |
| Glossaire | entrée FR/EN par métrique **réellement calculée** (D-093 ; mécanisme = panneau `<dialog>` du chrome depuis D-099). ⚠️ D-114 : la **prose des sections** reste FR (i18n = passe unique post-P2) |
| Strate par document (folds, CER par strate) | `DocumentRef.metadata["stratum"]` → `RunDocumentResult.stratum` (P0, D-110/D-111) |
| Comparer des profils de normalisation | système de **vues** existant : une vue par profil, un payload croise (les « deltas » 4g.1 = différences entre vues, zéro mécanique nouvelle) |
| Export nécessitant les **textes** (pas les scores) | couche **app** (seule à détenir corpus + `pipeline_outputs`) — ex. JSONL HIPE |

**Conventions transverses à toutes les tranches** (héritées des tranches T8-T13) :
payload + calcul + section + tests **dans le même commit** ; valeurs de tests
**dérivées à la main ou référence externe** (jamais Picarones comme oracle) ;
échantillons/listes dans les payloads **capés** (la source cape à 20/50 — garder
des caps explicites) ; tris déterministes ; clés de métriques **courtes**
(style `cer`, `mufi_err`) et **définitives à la 1ʳᵉ release** (contrat dur).

---

## Cible 4a — `structured_data`

| Aspect | Cible (PROVISOIRE) |
|---|---|
| **Scalaires** | `numseq_strict`, `numseq_value` — `Observation(value=score_global, weight=n_total)` ; `None` si GT sans séquence. *(`flesch_delta_*` : **abandonné** — arbitrage n°3, cf. §Abandons.)* |
| **Catégories** | **4** : `year`, `foliation`, `currency`, `regnal` — **`roman` retiré** (propriété 4b, cf. réparation R1) ; `regnal` garde `roman_to_int` en helper. |
| **Payload** | `StructuredDataPayload(kind="structured_data", per pipeline : per_category{n_total, n_strict, n_value, strict_score, value_score, lost_items[:cap]})`. Cap `lost_items` repris (50 → à confirmer). |
| **Section** | `reports/sections/structured_data.py` (table moteur × catégorie + bloc lisibilité — reprendre la lecture trafic-light/divergente de la source en jetons de charte). |
| **Données/packaging** | Regex + table de canonisation des devises = constantes du module (sourcées en docstring). |
| **Tests (valeurs main)** | Chaque regex : un positif/un négatif par catégorie (« 1515 » oui, « 0999 » non ; « f. 12r » ≠ « f. 12v » ; « an III » = 3) ; adaptatif : GT sans séquence → `None`. |
| **Glossaire** | + `numseq_strict`, `numseq_value` (FR/EN). |
| **Budget** | 1 module `metrics/structured_data.py` (détecteurs + 2 scalaires) ≈ 300 LOC + payload + section ≈ 150 — sous budget sans découpage. |

## Cible 4b — `philology` (dé-fragmentée)

| Aspect | Cible (PROVISOIRE) |
|---|---|
| **Architecture** | **Un moteur de préservation de marqueurs** + **tables en donnée** : `evaluation/data/markers_{abbreviations,early_modern,modern_archives}.yaml` (package-data) chargées par un loader unique. Deux stratégies de matching déclarées par table : `positional` (early_modern — opcodes equal) et `containment` (abbr/archives — strict verbatim + expansion à frontière de mot). Roman = détecteur dédié (parser porté de `roman_numerals.py`, 5 statuts). |
| **Scalaires** | `abbr_strict`, `abbr_expansion`, `early_modern_pres`, `archives_strict`, `archives_expansion`, `roman_strict`, `roman_value` — tous `Observation(value, weight=n_total_GT)`, `None` si GT sans signal (adaptatif). Noms courts **à figer à la tranche**. |
| **+ `hcpr` / `air`** *(SPEC_HIPE §9, arbitrage n°6 — **Q4 actée 2026-06-11**)* | `hcpr` = taux de préservation d'une **liste configurable de caractères archaïques** (généralisation paramétrable de `diacritic_err`/`mufi_err` — si factorisation en moteur commun, parité bit-à-bit exigée par test) ; **`air` = l'apport net** (Levchenko 2025) : taux d'occurrences de la liste dans la sortie **absentes de la GT** — détecte la sur-historicisation. **Une seule liste, archaïque uniquement** — défaut **`archaic_core`** trans-langue : `ſ ꝛ ⁊ ꝑ ꝓ ꝗ ꝙ ꝯ ꝝ ꝫ ꝭ þ ð ȝ` + `aͤ oͤ uͤ` ; **œ æ ß ç et accents modernes exclus du défaut** (langue-relatifs : « cœur » moderne → faux positif `air` ; perte = `diacritic_err` ; deux directions = classe taxonomy). **`air` actif par défaut** (`None` si la sortie ne porte aucun caractère de la liste) ; **`hcpr` visible seulement avec liste configurée** (anti-colonne-jumelle de `mufi_err`). Listes nommées en package-data (`archaic_core`, `archaic_de`, `archaic_fr_medieval`…) + override par run ; **nom + hash au manifeste/rapport**. Calculés sur vue `raw`/diplomatique ; pour les pipelines 2 étages, aussi sur l'étage brut (distinguer ce que le correcteur a perdu/inséré de ce que l'OCR avait déjà fait). Reste au build : dénominateur exact d'`air`. |
| **Payload** | `PhilologyPayload(kind="philology", per pipeline : par module {n_total, n_preserved(/strict/expansion), per_category{…}, missed[:cap], et pour roman per_status{5}})`. |
| **Section** | `reports/sections/philology.py` — **nouvelle** (il n'existe pas de section philologie aujourd'hui ; « étend la section philologie » du plan = étend l'offre philologique, la section naît ici). Les scalaires existants `mufi_err`/`cer_diplo`/`diacritic_err` restent où ils sont (by_engine) — la section 4b affiche les breakdowns. |
| **Réparations 🔶** | **R1 — roman compté une fois** : le comptage vit en 4b (5 statuts), `numseq` perd sa catégorie roman ; les scores strict/value sont **dérivés** des statuts (`strict = strict_preserved`, `value = n_total − lost`) — aucune perte. **R2 — `min_length=2` partout** (l'assiette `min_length=1` de la source compte `I`/`M` isolés). **R3 — expansion à frontière de mot pour TOUTES les longueurs** (la source ne borne que ≤ 2 lettres → `per` matche « permettre »). **R4 — pas de `try/except Exception` orchestrateur** (interdit par garde-fou) : chaque module est une métrique/un collecteur propre. |
| **Tests** | Tables : round-trip YAML + comptage d'entrées ; matching positionnel : cas main avec une substitution qui détruit un seul ſ ; containment : `ꝑ` strict vs « per » développé vs « permettre » (doit échouer après R3) ; roman : `ij→II` (j_dropped), `XIV→14` (converted), `IL` rejeté, dérivation strict/value depuis per_status. |
| **Glossaire** | + 9 entrées (les scalaires ci-dessus + `hcpr`/`air`). |
| **Budget** | moteur ≈ 250 LOC + roman ≈ 250 + payload/section ≈ 200 + 3 YAML — le YAML résout le cas `modern_archives` (601 → données). |

## Cible 4c — `textual_fidelity` (unifiée)

| Aspect | Cible (PROVISOIRE) |
|---|---|
| **Architecture** | **Un collecteur** `TextualFidelityCollector` (pattern Diagnostics) : `observe(pipeline, ref, hyp)` pendant la passe 1 ; à `build()` : (1) fréquences corpus depuis les réfs collectées → tokens rares (`max_freq=2`) → recall multiset par pipeline (+ échantillon `missed`) ; (2) table de modernisation lexicale (difflib, top-N tokens, variantes, `"∅"`). Résout proprement la « pré-passe corpus » : tout est calculé **après** la passe, sur les représentations déjà normalisées — zéro relecture, zéro mécanique nouvelle dans le runner. (3) *Sur-normalisation* : **déplacée en 4g.2** (bilan de correction, `SPEC_HIPE.md` §8) avec `error_absorption` — l'extraction avant/après (RAW_TEXT/CORRECTED_TEXT depuis `pipeline_outputs`, pattern calibration) vit en 4g, une fois, pour toutes les mesures. |
| **Scalaires** | Aucun en v1 (toutes les sorties sont des structures corpus-niveau ; un scalaire par-doc `rare_token_recall` exigerait le set rare avant la passe 1 — y revenir seulement si l'historique/le classement en a besoin). |
| **Payload** | `TextualFidelityPayload(kind="textual_fidelity", per pipeline : rare_tokens{n_rare_ref, n_recalled, recall, missed[:cap]}, modernization{top_tokens[:cap]{token, n_total, n_modernized, rate, variants}})`. *(`over_normalization` : déplacé en 4g.2 — `CorrectionPayload`.)* |
| **Section** | `reports/sections/textual_fidelity.py`. |
| **Réparations 🔶** | **R6 — câblage homogène** : un seul canal (collecteur), plus de calcul en couche rapport. *(R5 — bug C7 — et R7 — casse — suivent `over_normalization`/`error_absorption` en 4g.2.)* |
| **Abandons dans la famille** | `equivalence_profile` (C4 — mort + couvert par couche 2/D-089) ; `searchability_hooks` (déjà livré T11 ; `missed_tokens` sans consommateur). **Divergence assumée avec la lettre de la table 4c — à valider au lancement de la tranche.** |
| **Tests** | rare : corpus 3 docs calculé main (hapax/dis, multiplicité min()) ; modernization : « nostre→notre » + délétion `∅`. |
| **Glossaire** | + `rare_token_recall` (entrée descriptive même sans scalaire si la section l'affiche — règle D-093). |

## Cible 4d — `robustness` + `image_quality`

> **⚠️ Mis à jour au build.** **`image_quality` livré (4d.1, D-128).**
> **`robustness` ABANDONNÉ (4d.2, D-129)** — renversement assumé du verdict
> « GARDER » ci-dessous (ce guide l'autorise, cf. §Abandons) : dégradations
> *synthétiques* de validité douteuse, coût re-OCR disproportionné, seule feature
> à traîner la couche 6 + la tension CLI §8.4 ; la résilience *réelle* relève des
> **strates du dataset P3**. → **P2 terminée.** Détail : `MIGRATION_PLAN.md` D-129.

| Aspect | Cible (PROVISOIRE) |
|---|---|
| **Placement** | Dégradations = **fonctions pures seedées** (`Random(0)` conservé) — candidates `evaluation/robustness.py` (PIL whitelisté) pour la partie maths/courbes ; la **ré-exécution** des moteurs sur images dégradées vit **couche 6** (orchestrateur, réutilise les Modules existants — jamais d'import moteur en couche 3, la source l'avait déjà compris via l'injection). |
| **Opt-in & borne** | Pas de re-OCR implicite : option de `xerocr run` (ex. `--robustness noise,blur --robustness-docs 5`) plutôt qu'une commande dédiée (CLAUDE.md §8.4 fige la liste des commandes — à arbitrer à la tranche si une commande est plus honnête). Borne dure docs × niveaux × types documentée (défaut source : 10×6×5 = 300 exécutions). Compatible cache T15 (`resume`) : les images dégradées sont du contenu → adressage par empreinte fonctionne tel quel. |
| **Payload** | `RobustnessPayload(kind="robustness", cer_threshold, per pipeline × degradation_type : {levels, labels, cer_values(None-toléré), critical_level})` + `ImageQualityPayload(kind="image_quality", per document : {sharpness, noise, contrast, rotation_degrees, quality_score, tier}, agrégats{mean_*, distribution good/medium/poor})` — **scope corpus** (les features d'image ne dépendent pas du pipeline : ne PAS les modéliser en `MetricScore`). |
| **Sections** | `reports/sections/robustness.py` (courbes en tables/data-bars — pas de JS) ; bloc qualité image (même section ou dédiée — trancher au build). |
| **Réparations 🔶** | **R8 — constantes documentées** : 500 (variance laplacienne), 30 (MAD bruit), poids 0.40/0.30/0.20/0.10, ±10° — conventions éditoriales **sourcées en docstring** avec leur lecture (pas de fausse autorité scientifique). **R9 — pas de mock** : `generate_mock_quality_scores`/`generate_demo_robustness_report` ne sont pas portés (la démo XerOCR est octet-stable sans canaux environnementaux — précédent D-068). |
| **Abandons dans la famille** | `image_predictive` (C3) ; `robustness_projection` (hors plan, indépendance supposée). |
| **Whitelist archi** | + `PIL` (+ `numpy` si chemin rapide retenu — le fallback PIL-seul de la source permet de différer numpy) dans `test_layer_dependencies` **à cette tranche** (MIGRATION_COUCHE_3 §14). |
| **Tests** | dégradations : bytes→bytes déterministes (hash stable, seed) ; Otsu sur image bimodale synthétique main ; qualité : image générée (aplat vs damier) → bornes attendues ; courbe : moteur factice à CER scripté → niveau critique main ; **aucun re-OCR réel hors marker `live`**. |
| **Glossaire** | + `robustness` (niveau critique), `quality_score` (si affichés). |

## Cible 4e — `inter_engine` + `lines` + longitudinal raffiné

| Aspect | Cible (PROVISOIRE) |
|---|---|
| **inter_engine** | Fonction d'analyse inter-moteurs (scope corpus) : oracle/complémentarité depuis les représentations (collecteur léger ou réutilisation du `DiagnosticsCollector` qui détient déjà ref/hyp par pipeline — à trancher) ; divergence JS calculée sur les **comptages taxonomy déjà collectés** (`TaxonomyCollector` — zéro recalcul, formule log2 + ε=1e-12 + clamp [0,1] reprise). Payload `InterEnginePayload(kind="inter_engine", complementarity{oracle_recall, best_single_recall, best_engine, absolute_gap, relative_gap, per_engine_recall}, taxonomy_divergence{matrix, max_pair})`. Section : **étendre `cross_engine`** (lecture seule). 🔶 **R10 — GT vide → `None`** (pas 1.0) ; documenter « borne supérieure bag-of-words » dans la section (anti-surinterprétation). |
| **error_absorption** | **DÉPLACÉ → 4g.2** (bilan de correction, `SPEC_HIPE.md` §8) : intégré au `CorrectionPayload` — multiset GT-fondé (corrigées/introduites/conservées), complémentaire de CCR (GT-libre) et d'`over_normalization` (positionnel GT-fondé), sur l'extraction avant/après unique. |
| **lines** | Collecteur (mêmes textes normalisés que diagnostics — ⚠️ vérifier à la tranche que le profil de normalisation de la vue **préserve `\n`**, sinon prendre la représentation brute) : alignement F15 porté tel quel, percentiles p50-p99, Gini, `catastrophic_rate` seuils [0.30, 0.50, 1.00], heatmap 10 bins. Payload `LinesPayload(kind="lines", per pipeline : {percentiles, gini, catastrophic_rate, heatmap, line_count, mean_cer})`. Section `lines` (ou bloc de diagnostics). **`worst_lines` non porté** (couvert T11). |
| **longitudinal** | **Pas un payload `RunResult`** (c'est du multi-runs) : fonctions pures `evaluation/longitudinal.py` consommées par `app/history` (store tidy T7) → page `/history` + CLI `history`. OLS porté tel quel (conventions documentées : R²=1 si série constante). 🔶 **R11 — vrai test de rupture (Pettitt 1979)** à la place du max-diff : `U_t = Σ_{i≤t} Σ_{j>t} sgn(x_j − x_i)`, `K = max|U_t|`, `p ≈ 2·exp(−6K²/(n³+n²))` ; rupture signalée à `argmax|U_t|` **si p ≤ 0.05** (sinon « pas de rupture » — le max-diff, lui, « trouvait » toujours). Stdlib pur, déterministe, valeurs de test dérivées à la main + recoupées contre une implémentation publiée. |
| **Abandon** | `incremental_comparison` (C2). |
| **Glossaire** | + `oracle_gap`/`js_divergence` (si affichés), `gini` (lignes), `change_point` (page history si glossaire la couvre — sinon hors périmètre glossaire rapport). |

## Cible 4f — NER

| Aspect | Cible (PROVISOIRE) |
|---|---|
| **Extraction = brique de pipeline** (≠ post-traitement source) | `adapters/ner/spacy_extractor.py` : **Module Protocol** `RAW_TEXT|CORRECTED_TEXT → ENTITIES` (la NER est explicitement listée parmi les briques de pipeline, CLAUDE.md §3). Lazy import spaCy, paramètre `model` (défaut `fr_core_news_sm`), **version spaCy + nom/version du modèle → `RunManifest.module_versions`** (répare la reproductibilité, gratuit via l'enveloppe T6). Extra **`[ner] = ["spacy"]`** dans `pyproject.toml` (modèle téléchargé à part, comme les poids kraken — documenté). |
| **Fail-closed anti-silence** | (1) **Au plan** : demander un étage NER sans extra/modèle → `RunPlanningError` 422 « installer `xerocr[ner]` + `python -m spacy download <modèle>` » — jamais un run qui « réussit » avec `[]` (le silence source). (2) Sonde `engine_statuses` : extracteur listé, indisponible proprement sans extra (pattern kraken/pero). (3) GT entités présente mais NER non demandée → la métrique est simplement non applicable (`None`), pas un silence : l'utilisateur n'a rien demandé. |
| **GT & loader** | Sidecar **`.gt.entities.json`** (convention source reprise) → `GroundTruthRef(type=ENTITIES)` ; `representations.load_representation(uri, ENTITIES)` parse `{"entities": [...]}` ou liste nue, champs `{label, start, end, text?}` ; format invalide → erreur typée (pas un skip muet). |
| **Métrique & payload** | `metrics/ner.py` : matching IoU 0.5 greedy `(−score, ref_idx, hyp_idx)` + labels casefold, porté (algorithme inchangé) **après R14** — spans hypothèse reprojetés en coordonnées GT. Scalaire **`ner_f1`** (micro global, `Observation(value=f1, weight=n_entités_GT)`, `None` si GT sans entité) — jonction `(ENTITIES, ENTITIES)` que le registre type-driven accepte sans modification. Payload `NerPayload(kind="ner", iou_threshold, per pipeline : {precision, recall, f1, per_category{label: PRF+support}, missed[:cap], hallucinated[:cap]})`. Section `reports/sections/ner.py`. |
| **Réparations 🔶** | **R12 — bug C6 tué par construction** (payload typé). **R13 — pas de test circulaire** : valeurs PRF dérivées à la main (3 entités GT, 1 décalée IoU 0.6, 1 label différent, 1 hallucinée). **R14 — remap des offsets (C9)** : avant l'IoU, aligner hypothèse→GT au caractère (`rapidfuzz` opcodes — la mécanique d'`early_modern`) et reprojeter les spans hypothèse en coordonnées GT ; sans R14, le F1 mesure le profil ins/del de l'amont, pas la préservation des entités. Test dédié : insertion amont de 30 caractères → l'entité aval parfaitement transcrite reste TP. |
| **Glossaire** | + `ner_f1` (FR/EN). |
| **Hors périmètre** | Profil `hipe` (HuggingFace, jamais branché à la source) et backends multiples : un seul extracteur de référence ; le seam Module couvre les tiers. |

---

## Cible 4g — bilan de correction & conformité HIPE (nouvelle famille — [`SPEC_HIPE.md`](../../SPEC_HIPE.md))

| Aspect | Cible (PROVISOIRE) |
|---|---|
| **4g.1 — profils (couche 2)** | `hipe` (copie exacte de `norm()` : lowercase, ß→ss ꝛ→r œ→oe æ→ae aͤ→ä oͤ→ö uͤ→ü, césures DTA, non-`\w`→espace, compactage) + `heritage` (lowercase + ponctuation + espaces, **sans** mappings historiques) — 12 → 14 profils (donnée) ; vérifier au build si `heritage` se compose depuis `caseless`/`no_punctuation`. |
| **4g.1 — scalaire** | `cmer` (MER caractère = (S+D+I)/(H+S+D+I)) — comptes via `rapidfuzz.editops` (la plein-matrice maison serait trop chère au caractère) ; `Observation(weight=H+S+D+I)` → micro natif, macro depuis les par-doc. `mer` existant ≡ wMER : **mapping de nom à la frontière** (section/export), jamais de clé jumelle au registre. |
| **4g.1 — payload + section** | `ConformityPayload(kind="hipe")` : par pipeline {cmer/wmer micro+macro, `delta_norm = cmer_raw − cmer_hipe`, `delta_heritage = cmer_heritage − cmer_hipe`} — les deltas = **différences entre vues** (raw/hipe/heritage), zéro mécanique nouvelle ; section conformité lecture seule, profil mentionné sur chaque nombre. |
| **4g.1 — export** | adaptateur **JSONL HIPE en couche app** (le JSONL porte les TEXTES GT/raw/system, pas les scores → corpus + `pipeline_outputs` requis) ; `xerocr run --hipe-jsonl` ; c'est lui qui sert le leaderboard — le scorer runtime n'est pas nécessaire à l'interop. |
| **4g.1 — sémantique « absent »** | R-1.8 : dans cette famille, sortie absente → matérialisée `""` (erreur max) + warning ; partout ailleurs `None` = N/A — **double convention documentée**, docs dégénérés inclus au golden. |
| **4g.1 — golden** | `hipe-ocrepair-scorer==0.9.9` épinglé en extra `dev` (oracle de test, jamais runtime — arbitrage n°2) ; golden 1e-9 (scores ponctuels) sur job CI **3.12**, `skipif` explicite ailleurs ; property tests (CER ≥ cMER ; triplet Σ=1 ; pref = improvement−regression ; CCR=0 ⟺ system ≡ raw) + sensibilité Unicode (œ/oe, ſ/s, aͤ, césures) ; IC = bootstrap maison T9 (conformité = scores ponctuels). |
| **4g.2 — payload correction** | `CorrectionPayload(kind="correction")` par pipeline 2 étages : triplet {improvement, regression, no_change} + `catastrophic_rate` (seuil 0.10 conf.) · `pref`/`pcis` (+ `pcis_median` + comptage \|pcis\|>1) · `ccr`/`change_ratio`/`length_ratio` + drapeau `overedited` (> 2.0) · `char_ins_ratio` + `hallucination_heavy` (> 0.10) — dérivés des comptes cmer, pas un 3ᵉ alignement ; n'altère pas `ins_rate`/`del_rate` (niveau mot, cousins documentés) · **absorption** (ex-4e) · **over_normalization** (ex-4c) · éditions consécutives (médiane, max, part > 20) · échantillons capés. Pipeline mono-étage → payload absent avec mention, jamais un zéro muet. |
| **4g.2 — mécanique** | **Une** extraction avant/après (RAW_TEXT/CORRECTED_TEXT depuis `pipeline_outputs`, pattern `calibration_analysis`) partagée par toutes les mesures. |
| **4g.2 — procédure `hallucination`** | exécutée ici (arbitrage n°5) — décision retrait/conservation **avant la 1.0**. |
| **4g.2 — worst-pages** | extension du `DiagnosticsPayload` existant (T11) : tri par `delta_cmer` / `ccr` — consommateur déjà livré, ne pas recréer. Synergie : le payload `document_texts` (D-113) porte déjà les textes complets des pires documents — le diff pleine page des régressions 4g.2 le réutilise tel quel. |
| **Glossaire** | + `cmer`, `pref_score`, `pcis`, `ccr` (+ entrées correction affichées) ; une phrase documente la différence cer/cmer. |
| **Budget** | 4g.1 ≈ profils (donnée) + cmer (~60 LOC) + payload/section (~250) + export (~150) ; 4g.2 ≈ payload (~300) + section (~150) — sous budgets. |

## Ordre de tranches recommandé (PROVISOIRE — révisé 2026-06-11, plan A ; = ordre interne de **P2**, ex-Étape 4)

Chaque tranche = métriques + payload + section + glossaire + tests, **livrée
entièrement** (une sous-étape par session de construction). Contraintes **dures** :
4g.1 → 4g.2 (le triplet consomme `cmer` par-doc) · 4g.1 avant 4b (profil
`heritage`) · 4a avant/avec 4b (transfert roman) · 4d en dernier (orchestration).
Le reste est de la préférence.

| # | Tranche | Pourquoi à cette place |
|---|---|---|
| 1 | **4g.1** conformité HIPE (profils `hipe`/`heritage` · `cmer` · `ConformityPayload` + section · export JSONL · golden) | La valeur la plus haute : répare la comparaison la plus trompeuse du produit (VLM à CER > 100 %), pose les profils que 4b consomme, et porte l'argument de conformité de la 1.0 (plan A). Pas besoin d'« échauffement » : les patterns payload/section/scalaire-adaptatif sont déjà établis (6 payloads livrés, `mufi_err`). |
| 2 | **4g.2** bilan de correction (triplet · pcis+médiane · catastrophic · CCR/change/length · char_ins_ratio · absorption · over_normalization · éditions consécutives) | Consomme `cmer` (4g.1) ; absorbe les modules déplacés de 4c/4e ; **exécute la procédure `hallucination`** (décision avant 1.0). |
| 3 | **4a** `structured_data` (sans readability) | Petite, indépendante ; avant 4b (transfert de propriété du roman — entre les deux tranches, le roman n'est compté nulle part : acceptable et court). |
| 4 | **4b** `philology` (+ `hcpr`/`air`) | Consomme le profil `heritage` (4g.1) ; possède le roman ; introduit les tables YAML package-data. |
| 5 | **4c réduit** `textual_fidelity` (rare_tokens + lexical_modernization) | Collecteur corpus ; plus de dépendance avant/après (partie en 4g). |
| 6 | **4e réduit** `inter_engine` + `lines` + longitudinal/Pettitt (± `cev_jsd` si sa section est prête) | Réutilise les comptages taxonomy (JSD) ; Pettitt indépendant ; scindable 4e.1/4e.2/4e.3 si une session sature. |
| 7 | **4f** NER (avec R14) | Verticale autonome (adapter + extra `[ner]` + loader + métrique + section) ; permutable sans risque. |
| 8 | **4d** robustness + image_quality | **La plus lourde hors couche 3** : whitelist `evaluation/` PIL(/numpy) — Pillow est déjà une dépendance du projet (extra `[images]`, D-111) —, orchestration re-OCR couche 6, surface CLI à arbitrer. La garder pour la fin évite de bloquer les familles purement couche 3 derrière des décisions d'orchestration. Ses dégradations servent aussi de sonde de contamination (SPEC_HIPE Annexe C). |

---

## Risques de transfert & dettes à surveiller

| Risque | Où il frappe | Comment le détecter/le prévenir |
|---|---|---|
| **Clés fantômes** (C6/C7) | toute section | Tué par construction (payload Pydantic + section lisant des champs). Test : la section rend des valeurs non nulles sur un payload witness. |
| **Silence NER** (`[]` muet) | 4f | Fail-closed au plan (422) ; test « extra absent + étage NER demandé → erreur avec message install » ; jamais de skip silencieux dans le loader ENTITIES. |
| **Réimport de la fragmentation** | 4c, 4e | Garde-fou existant : pas de hooks, un seul canal (`analyses`). Revue : aucun calcul dans `reports/` (grep `evaluation.` import-only). |
| **Double comptage roman réintroduit** | 4a/4b | Test croisé : un texte avec `XIV` → compté en philology, **absent** du payload structured_data ; `min_length=2` unique. |
| **Alignements bag-of-words surinterprétés** | 4e (oracle), 4g.2 (absorption), 4c (rare) | Bornes documentées dans payload/section (« borne supérieure, ordre ignoré ») ; convention GT vide → `None` (R10). |
| **Lignes vs normalisation** | 4e lines | Vérifier à la tranche que la normalisation de vue préserve `\n` ; sinon représentation dédiée. Test : profil agressif + texte multi-lignes → line_count attendu. |
| **Non-déterminisme** | 4d (bruit), 4f (modèle spaCy) | Seed `Random(0)` porté + test hash stable des bytes dégradés ; version modèle dans `RunManifest.module_versions` + assertion dans le test adapter. |
| **Coût re-OCR non borné** | 4d | Opt-in + borne docs×niveaux×types dans la signature, testée (run sans flag → zéro exécution supplémentaire). |
| **Constantes magiques re-copiées sans source** | 4d, 4a, 4g | Chaque constante éditoriale (500, 30, poids, 0.20, [0.30/0.50/1.00], IoU 0.5, max_freq 2, seuils 0.10/2.0, caps 20/50) listée en docstring avec sa lecture — la revue refuse une constante nue. |
| **Tests circulaires** (le travers du renderer NER source) | toutes | Règle §5.8b déjà en vigueur : valeurs attendues dérivées à la main / référence publiée (jiwer, Pettitt 1979, scorer HIPE épinglé comme oracle *exécuté* — jamais comme source des attendus *écrits*), jamais la sortie de Picarones rejouée. |
| **Budget fichiers** | 4b, 4d | Tables → YAML (4b) ; si un module dépasse 600 LOC malgré tout → entrée justifiée `test_file_budgets` à la tranche, pas après. |
| **Clés de métriques bâclées** | toutes | Les noms courts proposés ici sont **PROVISOIRES** ; la tranche les fige **définitivement** (contrat dur rapports/JS/CSV/historique) — les choisir en début de tranche, pas en fin. |
| **`norm()` HIPE copiée inexactement** | 4g.1 | La pièce la plus sensible (sémantique `\w` Unicode, ordre des mappings, césures DTA) : golden 1e-9 épinglé (job CI 3.12, `skipif` explicite ailleurs — jamais un faux vert) + tests de sensibilité Unicode + docs dégénérés dans le golden. |
| **Double convention « absent »** (HIPE : vide = erreur max ; XerOCR : `None` = N/A) | 4g | La famille conformité matérialise l'absence en `""` + warning (R-1.8) ; partout ailleurs `None` reste `None` ; les deux documentées côte à côte — sinon les chiffres de conformité divergent du scorer sur run incomplet. |
| **Hygiène de clés pré-1.0 oubliée** | transverse | 3 décisions AVANT le gel des clés : `hallucination` (procédure à 4g.2), `searchability` (échelle AUTO — les valeurs baisseront vs runs passés, à faire pré-1.0 précisément), `flesch` (abandonné, journal D-0xx au 1ᵉʳ commit concerné). |
| **Surface 4g qui enfle** | 4g.2+ | Items T2 de la spec (`cev_jsd`, stabilité, folds) livrés **seulement avec leur consommateur** ; stabilité = différé d'enveloppe ; folds = canal strate livré (P0/D-110), seule la mécanique d'agrégation reste différée. |

## Abandons recommandés (à acter au lancement des tranches concernées)

| Module | Statut plan | Recommandation & motif |
|---|---|---|
| `image_predictive.py` | déjà abandonné (§Abandons #2) | **Confirmer**, motif corrigé (C3) : pas un stub mais une re-pondération sans pouvoir prédictif ni info nouvelle. |
| `robustness_projection.py` | absent du plan | **Abandonner** : interpolation linéaire de courbes synthétiques sur qualité mesurée + hypothèse d'indépendance — chaîne spéculative ; aucun manque si 4d livre courbes + qualité séparément. |
| `equivalence_profile.py` | listé en 4c **mais** déjà « mort » dans MIGRATION_COUCHE_3 §11 | **Abandonner** (C4) : zéro consommateur ; fonctionnalité couverte par profils couche 2 + preview YAML custom (D-089). **Divergence avec la lettre de la table 4c — à valider explicitement.** |
| `incremental_comparison.py` | absent de la table des gardées | **Abandonner** (C2) : exige des métadonnées « slots » hors enveloppe ; cas 180-pipelines inexistant ; réintroductible si un consommateur réel surgit (l'enveloppe `analyses` l'accueillerait). |
| `worst_lines.py` | non listé (couvert) | **Ne pas porter** : `DiagnosticsPayload.worst_lines` (T11) fait mieux (collecte au scoring, extraits verbatim, pas de re-split fragile). |
| `searchability_hooks.py` | non listé (couvert) | **Ne pas porter** : `searchability` livré (T11) ; `missed_tokens` sans consommateur. |
| `ner_backends.py` profil `hipe` + multi-backends | — | **Ne pas porter** : un extracteur de référence suffit ; le seam Module couvre les tiers. |
| `readability.py` (Flesch delta) | listé ✅ en 4a au plan | **Abandonner** (arbitré 2026-06-11, plan A) : construct hors domaine de validité — la segmentation en phrases s'effondre sur ponctuation OCR abîmée (deltas parasites) ; ce qu'il détecte (lissage/modernisation LLM) est mesuré directement par `lexical_modernization`, le bilan de correction 4g.2 et `hcpr`/`air`. **Réversible sans perte** (formules publiées — aucune deadline de gel). Amendement de la table 4a du plan, à acter au journal D-0xx au build. |

> Le gel de Picarones ferme la fenêtre : ces abandons sont proposés **en
> connaissance de cause** (chacun a été lu, pas présumé). Si une tranche les
> renverse, le journal D-0xx documente pourquoi.
