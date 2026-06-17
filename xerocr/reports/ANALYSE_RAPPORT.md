# Analyse — consolidation du rapport HTML

Guide durable. Établi après audit de la couche `reports` et revue de la vue de
référence Picarones (lecture seule). Objectif : **consolider, pas empiler** — un
rapport simple et standardisé, sans la dette accumulée.

## Audit (juin 2026)

**Sain (≠ chaos hérité)** : aucun shim/legacy/_v2 ; un `Section` Protocol unique ;
CSS centralisé (`html.py`) ; helpers partagés (`_tables`, `_style`, `engine_badges`).

**Le vrai signal — accumulation localisée (CSS), surtout dans la vue document** :
- ~40 classes bespoke `dd-*` (`dd-hl/lh/iq/ld/pct/sbs/diff/cers/fac/zoom…`) ;
- idiomes **dupliqués** : ~10 variantes de « barre » (`databar`, `dd-iq-bar`,
  `dd-lh-bar`, `dd-pct-track`, `bars-svg`, `comp-bar`…), 3 « chip », plusieurs
  « badge » ;
- **deux systèmes de drill-in parallèles** (`prof-*` profil moteur, `dd-*` document) ;
- **proportions non disciplinées** : SVG sans taille pinée qui s'étirent (cas
  `wmap-svg` : cellules géantes — corrigé en brique 1) ;
- **jargon dans l'UI** : le nom interne de vue `text` affiché brut (« Vue : text »).

Chaque mini-graphique a réinventé sa barre/chip/badge au lieu de réutiliser un
composant. Ce n'est pas Picarones, mais c'en est la pente.

## Principe de consolidation (non négociable)

- **Net-négatif** : la refonte **supprime** des classes/idiomes (preuve : diff CSS
  négatif, moins de familles). Elle n'ajoute pas une couche.
- **Primitives partagées** : un seul composant par concept — `metric_row`
  (badge | nom | valeur **tabulaire**), `bar`, `stacked_bar`, `chip`, `heatmap`,
  `stat_table` — dans `_style`/`_tables`.
- **Un seul drill-in** : fusionner `prof-*` et `dd-*`.
- **Cadre de section unique** : titre + 1 phrase « comment lire » + **libellé de
  vue humain** (fin du « text »).
- **Proportion** : tout SVG inline rend à une **taille bornée** (pinée ou
  intrinsèque + `max-width:100%`), jamais étiré au conteneur.
- **Garde-fou** : à terme, un test plafonnant les familles de classes (anti-récidive).

## Pertinence des tableaux Picarones (verdicts)

| Tableau | Verdict | Action |
|---|---|---|
| Confusions caractère par caractère (GT→OCR / moteur) | pertinent | **déjà là** (`CharConfusion`), à mieux présenter |
| Taxonomie d'erreurs (barres / classe) | pertinent (corpus) | présent, enrichir les classes |
| Profil leader vs runner-up (récupérabilité) | optionnel | différé |
| Matrice de corrélation entre métriques (Pearson) | gadget (bruit, colinéarité) | ne pas porter |
| Co-occurrence des classes (Jaccard) | gadget | ne pas porter |

## Métriques

- **CMER** existe (`conformity.py`) mais **gated** à la vue HIPE (`hipe`/`heritage`).
  À **exposer** (profil conformité au lanceur).
- **ICDAR** : CER/WER/MER sont les métriques de compétition ; pas de famille
  « ICDAR » nommée — ajouter une variante précise seulement sur demande.

## Tranches (consolidation, net-négatif)

- **S1.1 — proportion** ✅ : SVG à taille bornée ; `wmap` heatmap rendue à sa
  taille intrinsèque (fin des cellules géantes).
- **S1.2 — libellés de vue humains** ✅ : `view_label(view, lang)` dans `html.py`
  (**source unique**) ; `text` → « Texte brut », `diplomatic` → « Transcription
  diplomatique » ; vue déjà lisible (réf. OCR) rendue telle quelle. Routé dans
  **toutes** les sections (titres + cellules) — fin du « vue : text » brut. Le
  *cadre de section* uniforme (how-to-read homogène) est repoussé à S1.3 avec les
  primitives (mieux fait d'un coup que dispersé).
- **S1.3a — lisibilité « CER par moteur » (vue document)** ✅ : la liste CER
  était projetée au bord du panneau (`.dd-name{flex:1}` → valeur « trop
  éloignée »). Passée en **grille compacte** (badge · nom · valeur) : la valeur
  suit le nom dans sa colonne (alignée ET proche). 0 classe ajoutée, suppression
  de l'idiome `flex`.
- **S1.3b — primitive `track` (piste de proportion horizontale)** ✅ : 3 coques
  quasi-identiques (`dd-iq-bar`, `dd-pct-track`, `strata-bar`/`strata-fill`)
  fusionnées en **une** `.track` + `.track>i` (l'appelant pose largeur + couleur).
  Net −4 règles CSS, 3 consommateurs unifiés (qualité d'image, percentiles,
  strates). Non-spéculatif (3 consommateurs réels au moment de l'extraction).
- **S1.3c — primitive `chip` + `chips`** ✅ : `dd-hl-chip` (×8) et `preview-chip`
  fusionnés en `.chip` (+ rangée `.chips`). Net −1 règle, 2 sections unifiées.
- **S1.3d — vocabulaire de drill unifié + orphelin corrigé** ✅ : constat —
  les « deux systèmes » `prof-*`/`dd-*` étaient **déjà fusionnés** au niveau JS
  (`.drill-panel`/`.drill-back` génériques) et chrome (la vue document réutilisait
  `prof-*`). Dette réelle = **nom trompeur** (`prof-*` = profil moteur, mais
  partagé par les panneaux document) + **orphelin** (`.eng-back` stylé, mais le
  markup utilisait `.drill-back` → lien « ← retour » non stylé). Corrigé : chrome
  partagé `prof-{head,nav,title,pos,chart-title}` → `drill-{head,nav,title,pos}` +
  `drill-caption` ; `.eng-back` → `.drill-back` (orphelin résolu). `prof-row`/
  `prof-cell` (layout interne du profil moteur, non partagé) conservés.
- **S1.3 (suite) — restant** : `metric_row` (au 2ᵉ consommateur), *cadre de
  section* uniforme (titre + how-to-read homogène).
- **S1.4 — garde-fou** anti-prolifération de classes.

## Refonte mise en page du rapport — PLAN UNIQUE (juin 2026)

> **Remise à plat.** Les essais S2.1 (cap 1200 px) / S2.2 / brouillons multi-colonnes
> ont été soit **annulés** (le cap : l'utilisateur veut la **pleine largeur**,
> §D1), soit **conservés s'ils sont sains** (légende de composition groupée). Ce
> bloc **remplace** l'ancienne liste de tranches cumulées. Un seul plan, ordonné,
> avec les décisions explicitées **avant** tout code.

### Principe directeur (corrige le malentendu de départ)

Le problème n'est **pas** la largeur de la fenêtre — c'est l'**organisation des
données dedans**. On garde la **pleine largeur** (pas de cap arbitraire) et on
**remplit l'horizontale** : une longue liste se découpe en **plusieurs colonnes
côte à côte** au lieu de descendre tout en bas avec la droite vide. Référence de
calibrage : `design/screenshots/` (cartes denses, identité couleur par moteur).

### Problèmes (analyse complète, captures 1920 px + lecture du code)

| # | Problème | Cause (dans le code) |
|---|---|---|
| **D1** | Largeur : le cap 1200 px « rétrécit » et gâche l'écran | (corrigé) cap retiré → pleine largeur restaurée. Le vrai correctif est l'organisation (D2). |
| **D2** | Listes **tout en longueur**, droite vide (« mots ratés » ~40 l., « modernisation lexicale » ~25 l.) | tables/listes **mono-colonne** `width:100%`. → découper en **N colonnes côte à côte** (grille de sous-tables ; `columns` journal pour les listes). |
| **D3** | **Couleurs moteur absentes** là où elles devraient être | `engine_badges` (fern/slate/clay…) **n'est pas appliqué** dans `overview` (nom en texte brut, `overview.py:53`), `structured_data` (`:40`), ni partout en en-tête. Identité couleur **incohérente**. |
| **D4** | **Barres CER/WER « n'ont aucun sens et remplissent tout »** | `td.databar .db-fill` largeur ∝ valeur/max ; pour une **métrique d'erreur** (CER bas = bon), la **pire** valeur a la **plus longue** barre → contre-intuitif, sans légende, et remplit la cellule. |
| **D5** | **MUFI hors-sujet ; métriques ICDAR manquantes** | l'exemple a été généré avec le profil **`philologie`** (`cer_diplo, diacritic_err, mufi_err`…) — médiéval, **inadapté** à la presse XIXe. Le profil **`standard`** (`cer, wer, mer, searchability, hallucination, air`) conviendrait mieux. + colonnes **tout-`—`** (AIR/HCPR) qui encombrent. |
| **D6** | **Titres répétitifs** (« Texte brut — … » partout, « Classement (vue : Texte brut) ») | libellé de vue ressassé par section (S1.2) ; inutile en **vue unique**. |

### Cible = design canonique (captures fournies par l'utilisateur)

Deux écrans `design/` font foi (l'utilisateur les a transmis ; « on n'y est pas
encore ») :

- **« Par moteur »** : **tableau de métriques GROUPÉ** par thème (super-en-têtes :
  *Erreur · caractère* | *Erreur · mot* | *Philologique* | *Fiabilité
  documentaire* | *Calibration · aval* | *Économique*). Chaque colonne a un
  **indice d'échelle** (« 0→1 · ↓ erreurs », « ↑ rappel »…), une **barre subtile**
  derrière la valeur (**échelle commune par colonne**, légende explicite), et les
  **badges moteur colorés A→E**. Puis Dispersion + IC.
- **« Par document »** : **deux colonnes** — *fac-similé* (zoom) à gauche, *diff
  GT/sortie OCR* à droite (sélecteur de moteur en badges colorés, légende
  add/del/sub), et « CER par moteur · ce document » en badges colorés (meilleur
  surligné).

**Conséquence : le tableau de métriques n'est pas « minimal » mais RICHE et
ORGANISÉ.** Les barres **restent** (version canonique : subtiles, échelle commune,
légendées) — ≠ les barres actuelles qui « remplissent tout » sans sens.

### Métriques réellement calculables (registre)

`cer, cer_diplo, cmer, wer, mer, diacritic_err, mufi_err, air, hcpr,
searchability, hallucination, del_rate, ins_rate, numseq_*, region_*`. **CMER
existe** (réservé HIPE aujourd'hui — à exposer). Les colonnes canoniques *WIL,
Ligatures, Gini, ECE, F1 NER* sont **aspirationnelles** (calculées dans des
sections dédiées — calibration/NER/lignes — pas encore en colonnes de table) →
intégration ultérieure, pas bloquante.

### Réconciliation des 2 réponses utilisateur ⇄ canon

- **Barres (D4)** : réponse = « retirer ». **Mais le canon les garde** (subtiles,
  échelle commune, légendées). ⇒ je pars sur la **version canonique** (barres
  *correctes*, court = meilleur pour l'erreur, plafonnées, avec légende) plutôt
  que de les retirer — c'est ce que montre le design. **À confirmer d'un mot si
  tu préfères vraiment 0 barre.**
- **Métriques (D5)** : réponse = « il manque CMER et d'autres ICDAR ». ⇒ pas de
  set minimal : on vise le **tableau groupé canonique** avec les métriques **qui
  existent** — *Erreur caractère* : CER, CER diplo, **CMER** ; *Erreur mot* :
  WER, MER ; *Philologique* : diacritiques (MUFI **réservé** au médiéval, pas en
  défaut presse) ; *Fiabilité* : repérabilité, hallucination, AIR/HCPR. Colonnes
  tout-`—` **masquées**. WIL/Gini/ECE/F1 = ajout ultérieur.

### Ordre d'exécution (une tranche = un correctif, vérifié + commité seul)

1. **R1 — identité couleur moteur (D3)** ✅ : `engine_cell` (badge A→E coloré)
   appliqué dans les 7 sections qui affichaient un nom en texte brut — overview,
   structured_data, economics, conformity, textual_fidelity (rappel + flux),
   synthesis (meilleur + suivant), diagnostics (confusions). Ordre moteur global
   (`engine_order`) threadé. Couleur cohérente partout (comme le canon).
2. **R2 — tableau de métriques groupé (D4+D5)** — en sous-tranches :
   - **R2a** ✅ : **barres subtiles + légende** — `db-fill` passe d'un bloc qui
     remplit la cellule à un **fin trait de base** (position sur l'axe, échelle
     commune par colonne) + `bar_legend()` partagée sous overview/by_engine.
     Corrige le « n'a aucun sens et remplit tout ».
   - **R2b** ✅ : **masquer les colonnes tout-`—`** — `nonempty_metric_indices()`
     (distingue tout-None → masqué vs tout-zéro → gardé) appliqué à overview /
     by_engine / by_document. AIR/HCPR vides disparaissent.
   - **R2c** ✅ : **super-en-têtes thématiques** — `group_header_row()` fusionne
     les métriques consécutives d'un même groupe (Erreur·caractère / Erreur·mot /
     Philologique / Fiabilité / Structuré) en `colspan`. Appliqué overview +
     by_engine (cadrage `lead`/`trail` pour les colonnes hors-métrique). Pas de
     réordonnancement (profils déjà groupés).
   - **R2d** ✅ : **CMER exposé** au profil `standard` (calculé sur RAW_TEXT comme
     CER, MER caractère borné [0,1] — ≠ réservé HIPE) ; **MUFI** reste au seul
     profil `philologie` (médiéval). Exemple BNL régénéré en `standard` → CMER
     visible, MUFI absent (presse XIXe).
3. **R3 — organisation multi-colonnes (D2)** ✅ : remplir l'horizontale — « mots
   ratés » en **N tables côte à côte** (`_matrix_grid`, ~16 lignes/col, plafond 3,
   `.tcols`) ; « modernisation lexicale » en **colonnes journal** (`.wflow` →
   `columns:23em`, lignes insécables). Repli 1 colonne sur écran étroit.
4. **R4 — vue « Par document » deux colonnes** ✅ : fac-similé **à gauche** | diff
   GT/sortie **à droite** (`.dd-top2` grid), on lit le texte en regardant le scan ;
   sans image, le diff prend toute la largeur ; replie en 1 col < 860 px. (Les
   badges CER/moteur colorés sont déjà là via R1.)
5. **R5 — titres (D6)** ✅ (titres de section) : libellé de vue affiché **seulement
   si plusieurs vues** (vue unique → pas de ressassage). Fait pour overview,
   by_document, by_engine, gallery, dispersion (les h2/sous-titres proéminents).
   **R5-bis** ✅ : préfixes h3 des 12 sections analytiques (« Texte brut —
   composition/modernisation… ») traités via le helper partagé `view_prefix(view,
   lang, *, multi)` (« Libellé — » si multi, sinon ``""``). Appliqué à taxonomy,
   ner, calibration, philology, structured_data, lines, economics,
   textual_fidelity, correction, diagnostics, word_errors, et cross_engine
   (préfixe « Libellé · » pour ses titres vue·métrique). La colonne « Vue » de la
   table de significativité garde le libellé (c'est une donnée, pas un titre).
6. **R6 — diagramme de Venn du recouvrement** ✅ (parité Picarones) : `word_overlap_venn`
   (svg) rend un Venn **2-3 moteurs** des mots ratés par exactement chaque
   combinaison (cercles teintés par moteur, compte par région), compagnon visuel
   de la liste UpSet (qui reste la matière accessible). > 3 moteurs → `""` (liste
   seule). **Verdict « gadget » du début rétracté** : c'est la visualisation
   canonique du recouvrement, la donnée existait déjà.

### Reste (métriques — surface fonctionnelle, hors mise en page)

### Tranche M — métriques (décision utilisateur : « je veux tout »)

Surface fonctionnelle (≠ mise en page) : **5 ajouts métriques**, chacun sa
tranche (moteur couche 3 + branchement rapport + tests + gate). Ordre conseillé :

- **M1 — dégater la conformité (cmer/wmer micro · macro)** ✅ : `conformity.py`
  ancre = vue `hipe` **ou** première vue portant `cmer` (profil `standard` depuis
  R2d) → la section s'affiche sur tout corpus ; deltas norm/heritage **seulement**
  avec une vraie ancre HIPE + vues brute/heritage (sinon colonnes Δ masquées).
  Section retitrée « Précision bornée (cMER · wMER) » hors HIPE ; libellé de vue
  humain. Tests `test_conformity` mis à jour (gate = « aucun cmer → None »).
- **M2 — exactitude caractère & mot** : `char_accuracy = max(0, 1−CER)`,
  `word_accuracy = max(0, 1−WER)` (métriques `higher_is_better`, RAW_TEXT,
  réutilisent l'édition de CER/WER) + groupe « Exactitude ».
- **M3 — Flexible Character Accuracy (FCA)** : métrique ICDAR 2019 robuste aux
  réordonnancements — **nouvel algorithme** d'alignement (le plus lourd).
- **M4 — Bag-of-Words P/R/F1** : multiset de tokens (tp = Σ min comptes ;
  P = tp/|hyp|, R = tp/|ref|, F1) — RAW_TEXT, déterministe ; groupe « Recherche ».
- **M5 — brancher Region-F1 ICDAR 2015** : `layout.py` la calcule déjà ; section
  rapport quand un run de **segmentation** existe (sinon absente).

> ⚠️ Ce sont des tranches **moteur**, pas de la mise en page : à faire une par une
> (axe 2 — surface incrémentale), chacune vérifiée + commitée seule. Non démarrées
> en fin de session longue pour ne pas bâcler (cf. discipline anti-empilement).

Chaque R#/M# : analyse ciblée → 1 correctif → capture/golden de vérif → `make ci`
→ commit. **Cible visuelle = `design/screenshots/` (captures canoniques).**
