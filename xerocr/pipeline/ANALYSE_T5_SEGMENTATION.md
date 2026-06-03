# ANALYSE — Tranche T5 : structure / segmentation / mise en page

> **Nature** : guide de portage **durable** (session d'analyse, §9 `CLAUDE.md` —
> *ne code rien*). T5 est une **tranche verticale** qui traverse 4 couches
> (`domain` C1 · `formats` C2 · `evaluation` C3 · `pipeline` C4) ; ce doc vit en
> `pipeline/` car le **fan-out** (le cœur net-new de T5) y réside et `CLAUDE.md`
> ancre le déclencheur de `CanonicalLayout` à « la tranche segmentation (couche 4) ».
>
> **Deux parties, à ne pas mélanger (§9)** :
> 1. **ANALYSE DE LA SOURCE Picarones** — *durable* (Picarones gelé).
> 2. **DESIGN CIBLE XerOCR** — *périssable*, chaque verdict **« PROVISOIRE — à
>    confirmer au build »**. La construction se fera par **squelette ambulant**
>    puis épaississements, **jamais** en complétant une couche de haut en bas.
>
> **Autorité de statut = roll-up `MIGRATION_PLAN.md`.** Ce doc ne fige aucun statut.

---

## 0. Verdict d'ensemble (à lire en premier)

| Constat | Conséquence pour T5 |
|---|---|
| **Le fan-out par région N'EXISTE PAS dans Picarones** (segmentation = interne à chaque moteur, jamais exposée comme artefact ; aucun assemblage par région ; aucun routage par type de bloc). Confirmé par 4 explorations parallèles + `ANALYSE_COUCHE_4.md` L70-72. | Le fan-out est du **net-new** bâti **sur l'enveloppe déjà dimensionnée** (`Artifact.region_id`, `ArtifactType.LAYOUT`, `Module` Protocol). Rien à « porter » côté orchestration — **à concevoir**. |
| **XerOCR couche 2 est déjà *en avance* sur Picarones** : `AltoDocument`/`PageDocument` typés, géométrie **numérique** (pas de chaînes brutes : `coords: tuple[Point,…]`), parsers + writers, ordre de lecture PAGE en **arbre** (`ReadingOrderGroup.flatten()`). | T5 **n'a pas à réécrire le parsing**. Il ajoute : (a) `CanonicalLayout` en `domain`, (b) **mappers** `Alto/PageDocument → CanonicalLayout` + assembleur inverse en `formats`. |
| **Ce qui est portable de Picarones** = des **algorithmes purs** d'`evaluation` (stdlib/rapidfuzz, **zéro shapely/scipy/numpy**) : Region-F1 par IoU (`layout.py`), ordre de lecture F1 (`reading_order.py`), CER par ligne (`line_metrics.py`), projecteur ALTO→texte avec **dé-césure** `HypPart1/HypPart2`. | À **réimplémenter proprement**, pas copier (rupture nette §5.1). Adopter les **conventions saines** (niveau absent → `None`, micro-agrégat, appariement glouton déterministe). |
| **Le `Module.execute` renvoie UN artefact par type** (`dict[ArtifactType, Artifact]`). | Le fan-out (N régions → N `RAW_TEXT`) **ne peut pas** être un seul appel `Module`. Il vit dans **l'exécuteur** (C4) qui boucle sur les régions. **Le contrat `Module` ne change pas** → conforme au « test conceptuel » T5 (elle ne fait qu'**ajouter**). |

**Aucune contradiction détectée avec `CLAUDE.md` ni une couche mergée.** Deux
décisions ouvertes (géométrie en `domain` ; surfaçage du CER par-bloc dans
`RunResult`) sont signalées §F comme **points à trancher au build**, pas comme
conflits.

---

# PARTIE 1 — ANALYSE DE LA SOURCE PICARONES (durable)

## A. Modèle de mise en page

**Picarones n'a PAS de modèle neutre.** Types **format-spécifiques** indépendants
+ un `Region` dataclass *ad hoc* dans les métriques. Inventaire :

| Source | LOC | Rôle | À retenir |
|---|---|---|---|
| `formats/alto/types.py` | 126 | `AltoDocument/Page/TextBlock/Line/String` + `AltoBBox`. bbox pixels entiers, origine haut-gauche. **Pas de polygone**, **pas de neutre**. Césure via `subs_type=HypPart1/2`. | XerOCR a **déjà** ce modèle, **enrichi** (polygone + baseline + blocs `Illustration/Graphical/Composed` récursifs). |
| `formats/pagexml/types.py` | 82 | `PageDocument/Page/TextRegion/TextLine`. **coords = chaîne brute** `"x,y …"`, baseline idem, **niveau ligne** (pas de mot), régions imbriquées, `region_type` libre. | XerOCR a **déjà** ce modèle, **enrichi** : coords **parsées** en `tuple[Point,…]`, ordre de lecture en **arbre** (`ReadingOrderGroup`), régions génériques (`PageGenericRegion`). |
| `evaluation/metrics/layout.py` | 303 | **Seul** type géométrique agnostique : `@dataclass(frozen=True) Region(id:str, type:str, bbox:(x,y,w,h))` + IoU + appariement. | C'est un type **de métrique**, pas un modèle de page. Le neutre reste **à créer** (`CanonicalLayout`). |
| `evaluation/corpus.py` (≈ L200) | — | `ReadingOrderGT(region_order:list[str], source_path)` chargé d'un `.gt.reading_order.json`. | Vocabulaire d'ordre de lecture = **liste plate d'IDs**. |

**Coordonnées (durable)** : pixels entiers, origine haut-gauche, y vers le bas
(convention image, ALTO **et** PAGE). Valeurs négatives possibles (région
débordante). Réconciliation d'unités/résolution = **couche 3** (jamais en C1/C2).

## B. Parsers / writers ALTO & PAGE

| Source | LOC | Signature | Durable |
|---|---|---|---|
| `formats/_xml_utils.safe_parse_xml` | 57 | `(bytes) → Element\|None` (defusedxml, `forbid_dtd`) | XerOCR a son équivalent durci (`formats/_xml.py`, invariant §12). |
| `formats/alto/parser.parse_alto` | 227 | `(bytes\|str) → AltoDocument` | Tolérant versions v2/v3/v4/none ; `int(float(attr))` ; bbox négatif **clampé 0** ; déduplication `ComposedBlock` par `id()` objet (**fragile** — smell). |
| `formats/alto/writer.write_alto` | 148 | `(AltoDocument, version="v4", pretty=False) → bytes` | **Déterministe** si `pretty=False` (octet-stable → cache). XerOCR l'a déjà. |
| `formats/pagexml/parser.parse_pagexml` | 151 | `(bytes\|str) → PageDocument` | Namespace PRImA stocké brut ; 1ᵉʳ `<Unicode>` par ligne (variantes ignorées). |

**Smells durables à NE PAS reproduire** : (1) déduplication par `id()` objet
(parser ALTO) ; (2) duplication `_local()`/`_parse_int_attr()`/regex NS entre
parsers (à centraliser) ; (3) **PAGE sans writer** (XerOCR en a déjà un).

## C. Projecteurs « mise en page → texte » (clé du CER par région)

| Source | LOC | Forme | Durable |
|---|---|---|---|
| `evaluation/projectors/base.py` | — | `Protocol` projecteur + `ProjectionReport(ignored_dimensions, warnings)` | **Pattern à reprendre** : une projection **déclare ce qu'elle ignore** (géométrie, ordre…) → honnêteté du rapport (invariant produit). |
| `evaluation/projectors/alto.py` | 214 | `AltoToText` ; `alto_document_to_text(AltoDoc)→str` | **Dé-césure** `HypPart1/HypPart2` (utiliser `subs_content` sinon concaténer), ordre `Page→Block→Line→String`, espaces/`\n`/`\n\n`. **Logique dans le projecteur, pas le parser.** |
| `evaluation/projectors/pagexml.py` | 96 | `PageToText` ; `page_document_to_text(PageDoc)→str` | Ordre `Page→Region→Line`. |

## D. Métriques structurelles (algorithmes purs, portables)

| Source | LOC | Mesure | Niveau absent | Libs |
|---|---|---|---|---|
| `evaluation/metrics/layout.py` | 303 | **Region-F1 par type** (ICDAR 2015) : appariement **glouton par IoU** (seuil 0,5), P/R/F1 global + par type. `_iou_bbox`, `_align_regions`. | GT 0 région → `f1=None` (**pas 0.0**), `fp=len(hyp)`. | **stdlib seule** |
| `evaluation/metrics/reading_order.py` | 217 | **Ordre de lecture F1** : paires `(a avant b)` via `combinations`, intersection ref/hyp. | < 2 régions → `None`. | stdlib |
| `evaluation/metrics/alto_structural.py` | 175 | `alto_validity` (≥1 page∧bloc∧ligne) · `line_count_ratio` (min/max) · `word_box_coverage` (frac. mots avec bbox). | hyp vide → 0.0 ; 2 vides → 1.0. | formats |
| `evaluation/metrics/line_metrics.py` | 305 | **CER par ligne** : appariement **Levenshtein** (rapidfuzz, pas positionnel — *fix audit F15*), percentiles, Gini. | GT vide → zéros. | rapidfuzz |
| `evaluation/metrics/structure.py` | 238 | Fusion/fragmentation de lignes, ordre par **LCS** (rapidfuzz). | vide → 0. | rapidfuzz |

**Durable clé** : **aucune lib géométrique lourde** (pas de shapely/scipy/numpy) ;
le pixel-IoU/panoptique est noté « post-livraison » même dans Picarones. La
**convention « niveau absent → None »** (≠ 0.0 qui pénaliserait) est l'invariant
métier à conserver — il est déjà câblé dans le runner XerOCR (`_aggregate`
exclut les `None`).

---

# PARTIE 2 — DESIGN CIBLE XerOCR (périssable — PROVISOIRE)

> Chaque verdict ci-dessous est **PROVISOIRE — à confirmer au build** (le contact
> du code corrige souvent l'analyse). Conforme à : deux axes (enveloppe vs
> surface), « pas de consommateur = supprimé », budgets < 400 LOC, rupture nette.

## E. État de l'enveloppe XerOCR (déjà en place — NE PAS casser)

| Contrat | Fichier | T5 fait quoi |
|---|---|---|
| `ArtifactType.LAYOUT` réservé + `Artifact.region_id` optionnel | `domain/artifacts.py` | **les consomme** (matérialise le payload). |
| `Module.execute(inputs, params, ctx, ctrl) → dict[ArtifactType, Artifact]` (**1 artefact/type**) | `pipeline/protocols.py` | **inchangé** — segmenteur/recognizer/assembleur l'implémentent directement. |
| `PipelineExecutor.execute_document → dict[ArtifactType, Artifact]` (pool plat, dernier-par-type) | `pipeline/executor.py` | **étendu** (interne C4) pour le fan-out région — *ajout*, pas rupture. |
| `MetricSpec.input_types: tuple[ArtifactType, ArtifactType]` · `DocContext(reference, hypothesis: object)` | `domain/evaluation.py`, `evaluation/context.py` | une métrique `(LAYOUT, LAYOUT)` y entre **sans changement de contrat**. |
| `load_representation(uri, type)` (lève pour non-texte) | `evaluation/representations.py` | **+ branche `LAYOUT`** : parse ALTO/PAGE → `CanonicalLayout`. |
| `ProjectionSpec` (différé, 0 conso) | `domain/projection.py` | **1ᵉʳ consommateur** = projecteur `layout→text`. |
| `RunResult / MetricScore(metric, value, support)` | `evaluation/result.py` | accueille le CER-page (scalaire). *Le par-région = décision §F.* |
| `formats/_geometry.Point = tuple[int,int]` · `parse_points`/`format_points` | `formats/_geometry.py` | réutilisé par les mappers. |

## F. Décisions ouvertes (à trancher au build — PROVISOIRE)

| # | Décision | Options | Penchant PROVISOIRE |
|---|---|---|---|
| **F-1** | **Placement de la géométrie** de `CanonicalLayout` (Point/BBox/Geometry). `Point` vit aujourd'hui en C2 (`formats/_geometry`). | (a) `domain` possède Point/BBox/Geometry, `formats` importe ; (b) `domain` redéfinit `Point=tuple[int,int]` + `BBox`/`Geometry` frozen, `formats/_geometry` reste tel quel. | **(b)** : évite de toucher C2 (mergée) ; l'alias `tuple[int,int]` identique des deux côtés **n'est pas un shim** (type structurel, pas de conversion). La géométrie neutre **est** du vocabulaire transversal → légitime en `domain`. |
| **F-2** | **Forme de `CanonicalLayout`** : mono-page ou multi-page ? | (a) `CanonicalLayout.pages: tuple[LayoutPage,…]` (fidèle Picarones) ; (b) un `LayoutPage` = l'artefact (1 image = 1 page). | **(a)** pour l'enveloppe (le nom `LayoutPage` est listé séparément au backlog), **(b)** rempli au squelette (1 page). À **confirmer avec le 1ᵉʳ consommateur** (`MIGRATION_PLAN §8`). |
| **F-3** | **Surfaçage du CER *par bloc*** dans le rapport. `MetricScore` n'a pas de dimension région. | (a) squelette = **CER-page agrégé** seul (0 changement `RunResult`) ; (b) ajouter `region_id` à `MetricScore` **ou** un volet par-région à `RunDocumentResult` (additif). | **(a) au squelette** (prouve le chemin), **(b) en épaississement** si l'informativité le justifie. L'enveloppe **était dimensionnée pour la structure** → (b) reste un *ajout*, pas une rupture (test conceptuel T5 tenu). |
| **F-4** | **Découpe d'image par région** (crop) — besoin de pixels (PIL). | (a) squelette **`precomputed`** (régions + texte par région pré-fournis → **pas de crop, pas de PIL**) ; (b) crop dans l'exécuteur (PIL en C4 ?) ; (c) crop = concern d'un adapter (C5). | **(a) au squelette**. Pour le réel : **(c)** (le crop est une opération image → C5/adapter), à confirmer. **Ne pas** introduire PIL en `pipeline`. |
| **F-5** | **Routage par type de bloc** (moteur ≠ selon `region_type`). | (a) squelette = **1 recognizer pour toutes les régions** ; (b) mapping `region_type→adapter_name` dans la spec. | **(a) au squelette** ; (b) = épaississement avec consommateur réel (§5.3 : pas d'API « au cas où »). |

## G. Plan de tranche — squelette ambulant puis épaississements (PROVISOIRE)

**Squelette (pleine profondeur, largeur minimale)** — l'ordre est **intérieur→extérieur** :

| Étape | Couche | Livrable minimal | Garde-fou |
|---|---|---|---|
| 1 | C1 `domain` | `CanonicalLayout` (+ `LayoutPage/Region/Line/Word/Geometry/BBox/Point`) frozen, `extra=forbid`. **Mono-page rempli**, multi-page réservé (F-2). Testé en isolation (immutabilité, sérialisation). | < 400 LOC ; consommateurs réels **dans la même tranche** (mappers + métrique + exécuteur). |
| 2 | C2 `formats` | `alto_to_layout(AltoDocument)→CanonicalLayout` + `layout_to_alto(CanonicalLayout)→AltoDocument` (assemblage ; `write_alto` existe déjà). PAGE → incrément. | importe **uniquement** `domain` ; round-trip testé (golden ALTO octet-stable). |
| 3 | C5 `adapters` | source de layout **`precomputed`** (LAYOUT régions-seules) + recognizer **`precomputed`** par région (texte indexé par `region_id`). | même `Module` Protocol ; 0 dépendance lourde. |
| 4 | C4 `pipeline` | **fan-out** dans l'exécuteur : lit le `LAYOUT`, boucle régions → appelle le recognizer **1×/région** → collecte N `RAW_TEXT` **estampillés `region_id`** → étape d'assemblage `LAYOUT(+textes)→ALTO_XML`. **Échec partiel** : une région qui échoue n'abat pas la page (collecte les succès, région vide signalée). Ordre de lecture appliqué à l'assemblage. | `Module` **inchangé** ; structure de collecte région **interne C4** ; annulation coopérative respectée. |
| 5 | C3 `evaluation` | `load_representation` branche `LAYOUT` (parse→`CanonicalLayout`) ; projecteur `layout_to_text` (1ᵉʳ conso de `ProjectionSpec`, dé-césure portée de Picarones) ; métrique `(LAYOUT,LAYOUT)` = **appariement régions (id, sinon IoU glouton) → CER par région → micro-agrégat page**. **Niveau absent → `None`** (hyp sans lignes/texte). | algorithmes **réimplémentés** (rupture nette) ; whitelist C3 respectée (rapidfuzz OK, pas shapely). |
| 6 | C7 `reports` | la colonne de la métrique de structure apparaît **sans rendu modifié** (dividende du design générique, déjà vérifié en T7). | rapport octet-stable. |
| 7 | tests | archi (dès le 1ᵉʳ commit) + golden ALTO + round-trip + métrique sur **fixture layout-GT** (cf. risque R-2). | ruff + mypy --strict + pytest verts avant push. |

**Épaississements (1 concept/tranche, consommateur réel)** : segmenteur réel +
crop (F-4c) · routage par type (F-5) · mappers PAGE · CER **par-bloc surfacé**
(F-3b) · métriques de **détection de régions** (Region-F1 IoU, port `layout.py`) ·
ordre de lecture F1.

## H. Réflexe informativité-first (éprouvé en T7) — **bloquant**

Avant de câbler la métrique `(LAYOUT,LAYOUT)` dans un benchmark : **prouver
qu'elle est informative sur données réelles** (comme `cer_diplo`/`diacritic_err`/
`ins_rate` figeaient leur trouvaille). Sinon → écarter (§5.3, comme les ligatures
en #27).

---

## I. Risques de transfert & dettes à surveiller

| ID | Risque | Détection / désamorçage |
|---|---|---|
| **R-1** | **Sur-ingénierie du modèle** : recopier toute la richesse ALTO+PAGE « au cas où » (panoptique, glyphes, multi-page) → volume Picarones. | §5.3 : `CanonicalLayout` ne porte que ce que **mappers + métrique + assembleur** de **cette** tranche exigent. Glyphe/panoptique = différés. |
| **R-2** | **Pas de GT de mise en page committée** : le corpus BNL est **texte seul** (images/ALTO non committés, poids — `D-020`). La métrique structurelle n'a rien à mesurer en CI. | **Prérequis** : petite **fixture layout-GT** (1-2 ALTO/PAGE à régions, légère, committée). Sinon métrique non démontrable → ne pas câbler (R + H). |
| **R-3** | **Pool plat de l'exécuteur** : N `RAW_TEXT` même type écrasent le `dict[type→artefact]`. | Structure de collecte **par région** interne à C4 (ne PAS toucher le contrat `Module` ni `RunResult`). Test : un fan-out 3 régions produit 3 artefacts `region_id` distincts. |
| **R-4** | **PIL qui fuit en `pipeline`** via le crop. | Squelette `precomputed` (pas de crop) ; crop réel = concern adapter (F-4c). Garde-fou layer-deps. |
| **R-5** | **Déterminisme de l'appariement** (IoU à égalité). | Port du tri **glouton stable** de Picarones (candidats triés desc., 1-à-1) ; golden octet-stable. |
| **R-6** | **`CanonicalLayout` figé trop tôt** sur une forme qui ne sert pas le 1ᵉʳ conso. | Confirmer la forme **avec le squelette** (F-2), pas avant (`MIGRATION_PLAN §8`, corollaire inner→outer). |

---

## J. À transmettre à la session de CONSTRUCTION (3-5 points)

1. **Rien à porter pour l'orchestration** — le fan-out est **net-new** sur
   l'enveloppe existante (`region_id`, `LAYOUT`, `Module`). Le `Module` Protocol
   **ne bouge pas** : le fan-out boucle dans l'**exécuteur** (C4).
2. **Couche 2 est déjà faite et en avance** : T5 ajoute `CanonicalLayout` (C1) +
   **mappers** `Alto/PageDoc→Layout` & assembleur (C2). Ne **pas** réécrire les
   parsers/writers.
3. **Squelette = tout `precomputed`** (layout + texte par région) → pas de PIL,
   pas de crop, pleine profondeur C1→C7. Épaissir ensuite (F-1…F-5).
4. **Convention métier à tenir** : niveau absent → **`None`** (déjà câblé dans
   `_aggregate`) ; algorithmes **réimplémentés** (rupture nette), pas copiés.
5. **Bloquant avant câblage** : fixture **layout-GT** (R-2) + preuve
   d'**informativité sur données réelles** (H) — réflexe T7.
