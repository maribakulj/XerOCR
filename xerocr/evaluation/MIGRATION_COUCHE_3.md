# Plan de migration — Couche 3 (`evaluation/`) : Picarones → XerOCR

> Statut : **plan acté**, implémentation à venir. Lecture seule du code Picarones ;
> ce document fige les **contrats transverses** et les **décisions irréversibles**.
> Tout ce qui est local/réversible est explicitement **laissé au codage sous test** (§11).

---

## 1. Objectif & périmètre

La couche 3 calcule des **métriques** sur les sorties des pipelines (OCR/HTR/VLM, OCR+LLM)
face à une vérité-terrain, et produit un **`RunResult`** sérialisable + des données pour
le rapport. **Migration complète** (pas un MVP réduit) : on conserve toutes les vraies
métriques ; on ne supprime que le **mort / doublon / mal placé**.

Dépend des couches déjà mergées :
- **Couche 1 (domain)** : `ArtifactType` (dont `LAYOUT`), `Artifact`, `EvaluationView`,
  `MetricSpec` (contrat minimal), `EvaluationSpec`, `RunManifest`, `Corpus`/`Document`.
- **Couche 2 (formats)** : parsers/writers ALTO & PAGE (types riches : polygones,
  baselines, typage, **imbrication**, **arbre `ReadingOrder`** côté PAGE), `_geometry`
  (`Point`, `parse_points`), `text/normalization` (table canonique consolidée).

Ne fait **ni I/O, ni rendu, ni exécution de moteur** (cf. §3). Ce qui violerait cette
règle sort vers `adapters/` / `reports/` / `pipeline/`.

---

## 2. Principe directeur

**Un seul mécanisme**, **pureté de couche stricte**, **co-localisation** (une métrique =
un fichier autonome : fiche + fonction + test voisin). On décide **à l'avance uniquement**
ce qui est **transverse** (contrats) ou **irréversible** (formats de données persistés).
L'intérieur des métriques, le contenu des profils, les découpes de fichiers : **émergent
en codant**, sous test. La passe adverse a montré que seuls les retours du code révèlent
les vrais recoins — donc ce plan reste **lean**.

---

## 3. Noyau verrouillé (contraintes fondatrices actées)

1. **Registre unique type-driven.** On supprime les **4 systèmes parallèles** de Picarones
   (hooks `①`, registre module-level `③`, `@register_lever` `④`) ; il ne reste que le
   **registre instanciable** (`②`), sélection **100 % par `input_types`**.
2. **Deux formes de métriques** : **par-document** `(ref, hyp)` et **inter-moteurs**
   `(tous les EngineReports)`. **Agrégation par-moteur** : générique (moyenne/min/max/médiane)
   pour les scalaires, **agrégateur custom co-localisé pour les métriques struct** (dict).
3. **`DocContext` / `CrossEngineContext`** : un **sac d'entrées extensible** par forme.
   Une nouvelle entrée = un champ optionnel ; **zéro changement** aux métriques existantes.
4. **Fiche + fonction co-localisées** ; enregistrement par **décorateur pur** (construit un
   `Metric`, **ne mute aucun global**) + **collecte explicite par sous-paquet**.
5. **Sécurité scientifique obligatoire** (dette C) :
   - tout ratio/moyenne passe par **`safe_ratio` / `safe_mean`** (rendent `None` sur vide) ;
   - l'agrégation **exclut `None`** (jamais `0`) et **expose le *support*** (« 47/50 »).
6. **`scipy` en dépendance dure** (Wilcoxon/Friedman/OLS validés — pas de réimplémentation maison).
7. **`shapely` confiné** dans `evaluation/geometry.py`, **invoqué seulement pour les polygones**,
   et **dégradable** (`backend="shapely"` → repli bbox + `logger.warning` si absent).
8. **Persistance** : `schema_version` sur le **document `RunResult`** (chemin rapport/compare) ;
   **store longitudinal en lignes *tidy*** `(run, moteur, métrique, valeur, spec_version)`
   — additif par construction. Les deux sont **complémentaires** (cf. §8).
9. **Déterminisme bit-à-bit** : ordres triés, aucune horloge/aléatoire dans les sorties.
10. **`CanonicalLayout` : extension additive uniquement** (on ajoute des champs, on ne
    change jamais le sens d'un champ existant).
11. **Clés de sortie stables** : renommer un fichier/module est libre ; **renommer une clé
    de sortie de métrique est interdit** (contrat dur avec rapports/JS/compare).

---

## 4. G-A — La pièce porteuse : `CanonicalLayout` (prérequis bloquant)

État actuel : **`ArtifactType.LAYOUT` réservé**, décision « en `domain` » prise, mais
**aucune classe concrète écrite**. C'est le **prérequis n°1** de l'axe structure.

### Où
- **Le type `CanonicalLayout` → `domain/` (couche 1)** : type neutre, pur (Pydantic+stdlib),
  consommé par `formats` (production), `evaluation` (métriques), `reports` (affichage).
- **Les mappers `parse_alto_to_layout` / `parse_page_to_layout` → `formats/`** (couche 2 →
  domain autorisé) : produisent le `LAYOUT` à partir des arbres fidèles `AltoDocument` / `PageDocument`.
- **Le projecteur `LAYOUT → RAW_TEXT` → `evaluation/projectors/`** (axe texte).

### Forme proposée (sur-ensemble **fidèle** des types couche 2)

Calquée sur ce que les formats portent réellement (polygones, baselines, typage,
imbrication, hyphénation, arbre d'ordre de lecture) :

```
Geometry   : bbox? + polygon(tuple[Point])? + baseline(tuple[Point])?   # accès as_bbox()/as_polygon()
Word       : text, id?, geometry?, hyphen_role?(start|end), full_form?  # ALTO String ; PAGE: absent
Line       : text, id?, geometry?, words: tuple[Word]=() , confidence?  # text direct (PAGE) ou dérivé (ALTO)
Region     : id?, region_type?, kind(text|generic)=text, geometry?,
             lines: tuple[Line]=() , regions: tuple[Region]=()          # IMBRICATION (ComposedBlock / nested)
ReadingOrder: ordered: bool, items: tuple[str | ReadingOrder]           # arbre ; ALTO = groupe plat (ordre doc)
LayoutPage : id?, image_name?, width?, height?, regions, reading_order?
CanonicalLayout: pages, source_format(alto|page|other), source_profile?
             + has_word_level (property), full_text, iter_lines(), iter_regions()
```

### Choix de forme tranchés ici (transverses)
- **Ordre de lecture** : représenté en **arbre** (`ReadingOrder`), pour mapper fidèlement le
  `ReadingOrderGroup` PAGE ; l'ALTO mappe vers un **groupe ordonné plat** = ordre des blocs.
  → comble le « trou n°1 » de la passe adverse (côté PAGE déjà capté en couche 2).
- **Imbrication** des régions conservée (`Region.regions`) — les deux formats l'ont.
- **Régions non-texte** (`kind="generic"` : Image/Separator/Table) conservées.
- **Mots optionnels** : `Word` absent côté PAGE → `has_word_level` pilote le `None` gracieux.
- **Hyphénation** ALTO (`subs_type`/`subs_content`) remontée dans `Word` (champ optionnel).

### Mise à jour d'hypothèse (bonne nouvelle de la couche 2)
L'**ALTO de XerOCR porte `baseline` et `block_type`** (plus riche que Picarones). Donc
`baseline_coverage` et `region_detection.per_type` **peuvent fonctionner sur l'ALTO aussi**
— ils ne renvoient pas systématiquement `None`. La précondition (`requires`) reste pour les
formats qui ne **peuvent pas** porter la dimension.

---

## 5. G-B — Le registre unique (contrat)

### Fiche `MetricSpec` (réconciliation domain ↔ evaluation)
- **`domain/evaluation.py:MetricSpec`** reste le **contrat de type minimal** :
  `name`, `input_types`, `description`, `higher_is_better`. (déjà présent en couche 1.)
- **La couche 3 enrichit** avec les **métadonnées opérationnelles** (pas du domain) :
  `level`/forme, `profiles`, `tags`, `requires` (préconditions), `backend`, `unit`,
  `cost_hint`, `spec_version` — **chacune avec un lecteur nommé** (profil rapide, dégradation
  shapely, CSV, longitudinal). Pas de champ sans lecteur.
- **Co-localisation** : la fiche enrichie + la fonction vivent dans le **même fichier** de métrique.

### Signatures (deux formes)
```
DocumentMetric    : fn(ctx: DocContext)        -> float | dict | None
CrossEngineMetric : fn(ctx: CrossEngineContext)-> float | dict | None
```
Séparation **garantie par les signatures** (une métrique inter-moteurs reçoit des
`EngineReport`, jamais les documents) — **pas de police AST**.

### Enregistrement
Décorateur **pur** `@metric(...)` (→ construit un `Metric`, n'écrit dans aucun global) ;
chaque `metrics/<groupe>/__init__.py` **collecte explicitement** ses objets ;
`build_default_registry()` assemble. Aucun effet de bord d'import.

### Profils
`profiles.py` : un profil = **liste nommée explicite** **OU** **sélecteur de tags simple**
(`rapide`, `avancé`, + profils-métier). **Pas** d'algèbre include/exclude/cost. Vocabulaire
de tags **petit et validé**.

---

## 6. G-C — Le runner (deux passes + agrégation)

`evaluation/runner.py` (ex-`evaluation_engine`, + logique de calcul **rapatriée** de
`app/services/_benchmark_*` — l'app *appelle* l'évaluation, ne *calcule* plus) :

1. **Passe par-document** : `select(input_types)` → exécute chaque `DocumentMetric` sur
   `DocContext`. `None` = non applicable (skip).
2. **Agrégation par-moteur** : générique pour scalaires ; **agrégateur custom déclaré** pour
   les structs (confusion, taxonomie, calibration… — **ce n'est pas un cas rare**).
   `None` **exclu** ; **support** calculé.
3. **Passe inter-moteurs** : exécute chaque `CrossEngineMetric` sur `CrossEngineContext`
   (les `EngineReport` + corpus + tables) → **écrit dans le `RunResult`**.

---

## 7. G-D — Défenses (sécurité scientifique, dette C)

Défense en couches (cf. §3.5). En complément :
- **C4 — test générique** : fabrique des entrées dégénérées de chaque `input_types`
  (+ une entrée violant chaque `requires`) et **exige `None`** ;
- **C5 — golden** sur fixtures réelles **ALTO + PAGE + texte** ;
- **C7 — checklist de revue** (filet pour le résidu, surtout contributions externes).

Acté : la dette n'est **pas éliminable** (un faux chiffre plausible est indiscernable d'un
vrai) ; on la rend **locale, visible au CI (support + diffs golden), bornée**. Risque
**présent dès maintenant** sur les métriques structurelles (mélange ALTO/PAGE) → `safe_*`
et préconditions dès le jour 1.

---

## 8. Résultat & persistance

- **`evaluation/result.py:RunResult`** (ex-`benchmark_result`, dégonflé) = contrat de sortie
  unique, avec **`schema_version`** + upcaster (protège le chemin rapport/compare, y compris
  les vieux fichiers JSON sauvegardés).
- **`cross_engine`** : nombres **écrits dans le `RunResult`** (le HTML/CSV/JSON lisent les données).
- **Store longitudinal** : **lignes tidy** (ajout de métrique = nouvelles lignes ; rien ne casse).
  Le store SQLite vit en **`adapters/storage`** (pas en couche 3).
- **Coexistence** : « jeu de champs fait foi » (note couche 2) = même esprit que le tidy pour
  les **ajouts** ; `schema_version` couvre l'autre cas, les **changements structurels** du
  document `RunResult`. Ne pas laisser la convention « pas de version » déborder sur le document.

---

## 9. Inventaire source → cible (Picarones `evaluation/`, 93 fichiers)

**Supprimés (18)** — 4 registres + plomberie (`metric_hooks`, `builtin_hooks`,
`builtin_metrics`, `metric_registry`, 4×`*_hooks`), doublons (`search`), morts
(`equivalence_profile`, `alto_metrics`, `cost_projection`, `ner_backends`, `difficulty`,
`module_policy`), `normalization` (consolidé en `formats/text`).
⚠️ **Supprimer une métrique n'est pas local** : nettoyer ses références côté
`reports`/JS/CSV/glossaire (ex. clé `difficulty_score`).

**Changés de couche (≈5)** — `history` (SQLite) → `adapters/storage` ; `cdd_render` (SVG),
`worst_lines` → `reports` ; `levers` (4ᵉ registre) → `reports/narrative` ; ré-exécution
moteur de `robustness` → `pipeline`.

**Modifiés (≈22)** — renommages (`benchmark_result`→`result`, `evaluation_engine`→`runner`,
`_diff_utils`→`diff`, …), **splits >400 LOC** (`modern_archives`, `roman_numerals`,
`numerical_sequences`, `inter_engine`), réécriture structure sur `LAYOUT`
(`layout`→`region_detection`, `reading_order`, `alto_structural`→`geometry_coverage`),
dédoublonnage (`searchability` absorbe `search`), `reliability`→`multirun_stability` (κ/α morts retirés).

**Gardés (≈35)** — le noyau métier réel (CER/WER, philologie, inter-moteurs, économie, image,
longitudinal) ; **clés de sortie inchangées**.

**Nouveaux (8)** — `geometry.py` (shapely), `profiles.py`, `metrics/_helpers.py` (`safe_*`),
`structure/region_detection.py`, `structure/line_detection.py`, `projectors/layout.py`,
`gt_types.py`, + `__init__` de sous-paquets.

**Organisation cible** : `metrics/{text, philology/, structure/, cross_engine/, economics/,
image/, longitudinal/}`, `statistics/`, `views/`, `projectors/`.

---

## 10. Risques de transfert Picarones → XerOCR

1. **`reading_order` sans source** (Picarones) → **résolu en couche 2** côté PAGE (arbre
   `ReadingOrder`) ; ALTO = ordre de bloc implicite → groupe plat dans le mapper.
2. **Agrégateurs custom** (confusion/taxonomie/calibration) — **pas des moyennes** ; prévoir
   l'agrégateur custom comme chemin normal des structs (§6).
3. **Clés de sortie = contrat dur** avec reports/JS/compare (§3.11).
4. **`benchmark_result`→`RunResult`** : ~30 consommateurs côté reports/web/compare —
   beaucoup meurent (shim, workflows), mais **migrer reports + web + compare JS en bloc**.
5. **Consolidation `normalization`** : **sans danger** (l'`evaluation/normalization.py` de
   Picarones ne définit aucun profil ; tout est en `formats/text`).

---

## 11. Explicitement laissé au codage (sous test)

- L'intérieur de chaque métrique (algorithme).
- Le **contenu** des profils `rapide`/`avancé` et le **vocabulaire de tags**.
- La **liste des métriques structurelles PAGE-natives** à ajouter.
- Les découpes exactes des fichiers >400 LOC.
- Les coutures de câblage (pré-passe stats corpus → `DocContext` pour `rare_tokens` ;
  alimentation des données d'historique → passe longitudinale/`baseline_comparison`).

---

## 12. Tests & budgets

- **Architecture** : étendre la whitelist `evaluation/` (+`scipy`, +`shapely`, +`jiwer`,
  +`rapidfuzz`, +`numpy`, +`PIL`) ; ajouter `no-side-effect-import` (décorateur = valeur pure)
  et `file-budgets` (>400 LOC = entrée justifiée).
- **Golden** : `RunResult` canonique sur **ALTO + PAGE + texte** ; déterminisme bit-à-bit.
- **Sécurité** : le **test générique d'entrées dégénérées** (C4) ; conformité CER/WER vs `jiwer` ;
  ALTO/PAGE → `LAYOUT` round-trip de fidélité (aucune dimension visée perdue).

---

## 13. Ordre d'implémentation (bas-en-haut)

1. **`CanonicalLayout`** (domain) + mappers `alto/page → layout` (formats) + projecteur `layout → text`.
2. **Registre** (`registry.py` + décorateur pur + `profiles.py`) + **`DocContext`/`CrossEngineContext`** + **`_helpers.py`** (`safe_*`).
3. **`runner.py`** (2 passes + agrégation générique/custom + `None`-exclu + support).
4. **`result.py:RunResult`** (+ `schema_version`).
5. **Métriques texte** d'abord (CER/WER + portage du noyau, clés stables), **puis structure**
   (`region_detection`, `line_detection`, `reading_order`, `geometry_coverage`).
6. **`cross_engine`** (écriture dans `RunResult`) + **statistiques** (scipy).
7. **Store longitudinal tidy** (via `adapters/storage`) + profils + reste des métriques.

---

*Référence : décisions actées lors de la session de conception couche 3. Ce document est le
contrat ; l'implémentation suit l'ordre §13, le reste émerge sous test (§11).*
