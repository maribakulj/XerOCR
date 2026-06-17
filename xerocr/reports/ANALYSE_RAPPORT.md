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

## S2 — largeur, densité, hiérarchie (analyse, juin 2026)

Captures réelles (Playwright, viewport **1920 px**) + comparaison à la spec
canonique `design/` (rendue **bornée à 1200 px**). Le rapport est **sain en
structure** mais **mal calibré en largeur** : sur grand écran il s'étale et
devient illisible. Problèmes, du plus structurant au plus local :

| # | Problème | Cause (preuve) | Correctif visé |
|---|---|---|---|
| **P1** | **Tout s'étire pleine fenêtre** (gouttières géantes, barres de 700 px, colonnes repoussées au bord) | `body.report-board` n'a **ni `max-width` ni centrage**. La spec canonique impose `.report-board{max-width:1200px;margin:0 auto}` (`design/render/render.js:43`) — **absent du rapport réel**. | **Caper la colonne** ~1100–1200 px, centrée. **Corrige toutes les sections d'un coup.** |
| **P2** | **Barres de données démesurées** (`table.data` databar ∝ largeur de colonne ; légende taxonomy : nom à gauche, % au bord droit) | barre = % de la cellule, cellule = 1/n de la largeur → barre absurde quand large ; légende en `space-between` pleine largeur. | borne la barre (largeur fixe ~120 px, valeur **collée**) ; légende en grille compacte. |
| **P3** | **Sections « verticales » trop longues** : « Carte des mots ratés » (~40 lignes), « modernisation lexicale » (~25 mots × variantes) = murs verticaux qui **gâchent l'horizontale** | listes mono-colonne. | passer ces listes en **multi-colonnes** (CSS `columns`/grid responsive) → utilise la largeur, réduit la hauteur. C'est le sens de « s'adapter à l'horizontale ». |
| **P4** | **Titres répétitifs / qui s'enchaînent mal** : le libellé de vue est ressassé partout (« Classement (vue : Texte brut) », « Texte brut — composition… », « Vue : Texte brut ») | suffixe/préfixe de vue **systématique** par section (S1.2). Inutile quand il n'y a **qu'une vue** (cas courant). | afficher le libellé de vue **une seule fois** (bandeau d'onglet/section) ; retirer le ressassage des titres quand vue unique. Clarifier la hiérarchie h2/h3/`drill-caption`. |
| **P5** | **Grands vides verticaux** (≈ 1/3 de page vide sous l'overview en 1920) | conséquence de P1 (contenu étroit en réalité, conteneur large). | résolu par P1 ; ajuster les gaps ensuite. |

**Inspiration canonique** (`design/screenshots/report-by-engine.png`) : board
**borné centré**, cartes denses, **barres courtes dans les cellules**, hiérarchie
nette (eyebrow + titre display + sous-titre). On reproduit ce calibrage.

### Tranches S2 (disciplinées, net-négatif quand possible)

- **S2.1 — largeur max + centrage du board** ✅ : `body.report-board` passe en
  `align-items:center` + `.report-chrome,.report-main,.compare-bar{max-width:1200px}`
  (calage sur la spec canonique). Corrige P1 **et** P5 pour **toutes** les sections
  d'un coup ; le fond (trame) reste pleine page. Vérifié en capture 1920 px.
- **S2.2 — légende de composition groupée** ✅ : `.comp-row` passait le label
  en `1fr` → valeur (`%`/compte) projetée au bord droit. Passé à
  `14px 132px auto auto 1fr` (spacer final) → swatch·label·part·compte **groupés
  à gauche**, lisibles. (Les data-bars de `table.data` sont redevenues correctes
  via S2.1 — pas de plafond séparé nécessaire.)
- **S2.3 — libellé de vue affiché une fois** (P4) : retrait du suffixe
  systématique dans les titres (raffine S1.2 dans le bon sens : une seule
  surface d'affichage), hiérarchie typographique clarifiée.
- **S2.4 — sections denses en multi-colonnes** (P3) : « mots ratés » +
  « modernisation lexicale ».
