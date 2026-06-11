# Plan UI/UX — Rapport interactif : de la coquille à la cible `design/`

> **Statut : plan validé** (recommandations ★ retenues, décision IA (c) validée —
> D-096). Complète `DECISION_RAPPORT_INTERACTIF.md` (D-094, le *cadre*) par le
> *design d'expérience*. La source visuelle canonique est **`design/`**
> (`tokens.css` + `chrome.jsx` + 4 vues JSX + screenshots — D-018) : ce doc mappe
> chaque élément de la cible sur (a) sa faisabilité données, (b) son implémentation
> disciplinée, (c) sa tranche.
>
> **Ce doc porte LA file unique du chantier rapport** (§4) : il remplace toute
> numérotation antérieure de tranches (le pointeur « tranche 2 = graphes SVG »
> de D-095 ≙ U2 ici ; les « tranches 3/4 images » de D-094 ≙ T3/T4 en queue de
> file). Pas de double comptabilité : une seule séquence, U1 → … → T4.
>
> **Décision IA (D-096, validée)** : les **4 onglets sont confirmés**
> (Vue d'ensemble / Par moteur / Par document / Croisements — option (c)), avec
> deux amendements : (1) la **significativité apparaît inline dans le verdict**
> (badges « écart significatif / non séparable » sur le classement de la Vue
> d'ensemble — le verdict n'est jamais lu sans sa qualification ; Croisements
> reste l'approfondissement, et accueillera la famille inter-moteurs de
> l'étape 4e) ; (2) **règle de croissance** : *un onglet = une question, une
> section = une réponse* — chaque famille de métriques de l'étape 4 atterrit
> dans l'onglet de la question qu'elle éclaire (fidélité/philologie → Moteurs ;
> lignes/pires-cas → Documents ; inter-moteurs → Croisements), jamais un onglet
> par famille.

---

## 1. Diagnostic — écart rendu actuel ↔ cible `design/`

| # | Aspect | Actuel | Cible (`design/`) | Nature |
|---|---|---|---|---|
| 1 | Chrome | barre noire : wordmark + titre | wordmark + **onglets intégrés** + méta (docs/moteurs/date) + **boutons ⬇CSV ⬇JSON** (`chrome.jsx`) | visuel/fonctionnel |
| 2 | Onglets | barre pilule **séparée**, mono 12px | **dans le chrome**, fond translucide, `--sans` 12px **medium**, actif = pilule `--paper` (`tokens.css:166`) | visuel |
| 3 | Anatomie de vue | h2 empilés dans **un seul** méga-panneau `.sec` | **héros de vue** (eyebrow `VUE 0n · NOM` + titre display + desc + stats) puis **cartes `.sec` distinctes**, parfois en grille 2 col. (`HeroBand`, vues JSX) | structurel |
| 4 | Onglet Documents | table dense d'abord, galerie passive ensuite | **galerie = l'entrée** (cartes cliquables) + filtres strate + toggle ⊞ Grille / ≡ Liste ; table = le mode Liste | **UX (inversion)** |
| 5 | Drill-in | aucun | **profil moteur** (clic ligne → KPIs, CER/doc, calibration, composition) et **détail document** (fac-similé + CER/moteur + diff avec sélecteur de moteur, prev/next, ← retour) | UX/fonctionnel |
| 6 | Glossaire | section toujours en bas | la cible dit : « **survoler pour la définition** » (en-têtes de table, `view-by-engine.jsx:87`) | UX |
| 7 | Tables | statiques | **triables** (clic en-tête, flèches ↑↓, chip « ORDRE ACTIF », réinitialiser) ; « cliquer une ligne pour ouvrir le profil » | fonctionnel |
| 8 | Graphes | aucun (tables) | dispersion min/méd/µ/max, courbe calibration, CER/doc trié, composition d'erreurs | fonctionnel (T2 actée) |
| 9 | Strates | inexistantes au rendu | composition du corpus (%, n), chips de filtre, CER par strate | **données manquantes** |
| 10 | Exports | CSV en CLI seulement, JSON côté web | boutons dans le chrome | fonctionnel |

---

## 2. Principes UX (le « pourquoi » avant le « quoi »)

1. **Le rapport répond à 4 questions** — c'est l'IA des onglets :
   *Qui gagne ?* (Vue d'ensemble) · *Comment se comporte chaque moteur ?* (Par
   moteur) · *Où ça casse, sur quelles pages ?* (Par document) · *Les écarts
   sont-ils réels ?* (Croisements).
2. **Trois espaces de navigation, jamais mélangés** :
   - **vues** = onglets (changer de question) ;
   - **objets** = drill-ins (zoomer sur *un* moteur, *un* document — avec
     « ← retour », prev/next) ;
   - **périphérie** = chrome (méta, exports, compare, glossaire, palette) —
     accessible partout, jamais dans le flux de lecture.
   Le glossaire en bas violait ça : c'est de la périphérie, pas du flux.
3. **Pyramide de l'évidence** : chaque vue ouvre sur le verdict (héros + readouts),
   puis le détail (tables/graphes), puis la preuve (drill-in). Jamais l'inverse.
4. **La définition vient au point d'usage** (survol d'un en-tête), pas dans un
   appendice. Le glossaire YAML existant devient la *source* de ces tooltips.
5. **Discipline D-094 inchangée** : le serveur rend tout ; le JS révèle/trie/
   navigue, ne construit jamais ; un script CSP-hashé ; dégradé propre sans JS.

---

## 3. Propositions par chantier

### A. Chrome unifié ⚖️

- **A1 ★ (= la cible)** : onglets **dans** la barre noire (`tokens.css` les stylise
  déjà : fond `rgba(paper,0.08)`, actif pilule paper/ink, `--sans` 500) + méta
  `n docs · n moteurs · date` (du `RunManifest`) + boutons **⬇CSV ⬇JSON**.
- **A2** : garder la barre séparée, la rendre sticky. — Rejeté : double bandeau,
  diverge de la source canonique sans raison.
- **Exports** ⚖️ : (a) `href="data:…"` zéro JS mais **double le poids** du fichier
  (le JSON y serait deux fois) ; **(b) ★ Blob depuis l'île de données** (~10 lignes
  JS) — l'île `RunResult` arrive de toute façon (D-094), le CSV se dérive client
  des mêmes données (ou 2ᵉ île CSV si plus simple, à trancher au build).

### B. Anatomie de vue : héros + cartes ⚖️

- Casser le **méga-`.sec`** : `render_document` n'enveloppe plus tout dans une
  carte unique ; chaque section rend **sa** carte.
- **Héros par onglet** (serveur) : eyebrow `VUE 01 · VUE D'ENSEMBLE`, titre
  display, description, 2-3 stats à droite — calculés du `RunResult`.
- **B1** : générique — chaque section = une carte, grille auto. Simple mais ne
  donne pas les compositions de la cible (Identité ⟷ Composition côte à côte).
- **B2 ★** : une **couche « vue » mince** en couche 7 : chaque onglet a un
  compositeur (fonction, pas un nouveau Protocol) qui place le héros + arrange
  ses cartes de section (grilles où la cible le dicte). Le `Protocol Section`
  reste le seul contrat de **contenu** ; la vue n'est que de l'**agencement**.
  C'est l'évolution structurelle clé — sans elle on n'atteint jamais la cible.

### C. Onglet Documents : la galerie devient l'entrée ★ (décision utilisateur)

- **Galerie en tête** (cartes cliquables), **table `by_document` = mode « ≡ Liste »**
  derrière un toggle ⊞/≡ (comme la cible). Plus de doublon visuel.
- **Détail document au clic**, livré en deux temps honnêtes :
  - *dès maintenant* (« détail léger », données déjà là) : CER par moteur (barres),
    scores du doc, pires lignes **de ce doc** si présentes dans `diagnostics` ;
  - *T3/T4 (D-094)* : vignette réelle puis fac-similé medium + **diff complet**
    avec sélecteur de moteur (borné par budget hors-ligne).
- **Mécanique drill-in** ⚖️ : (a) `<details>` inline sous la carte — zéro routing
  mais pas de « page » ni prev/next, à l'étroit ; **(b) ★ panneaux serveur cachés
  + hash** (`#doc-<id>`) — donne « ← retour à la galerie », prev/next, deeplink
  partageable, cohérent avec les onglets (même pattern révéler/cacher). Le nombre
  de panneaux détail suit le **budget** D-094 (pas un panneau par doc à 5000).

### D. Profil moteur (drill-in n°2)

Clic sur une ligne du tableau → panneau profil : bande KPI (CER médian/étendue,
WER, ECE, €/1000p — données présentes), CER par document (graphe T2), courbe de
calibration (payload existant), composition d'erreurs (payload taxonomy). 5-10
moteurs → panneaux cachés **toujours** bon marché (pas de question de budget).
Prev/next + « ← retour au tableau ». Même mécanique hash que C.

### E. Glossaire : contextuel, plus jamais en appendice ⚖️ (décision utilisateur)

- **E1 ★** : **définitions au survol des en-têtes** de métriques — `title=` (ou
  tooltip CSS enrichi) alimenté par `glossary/{fr,en}.yaml`. C'est littéralement
  ce que la cible écrit (« survoler pour la définition »). Zéro JS.
- **E2 ★ (complément)** : entrée « Glossaire » **dans le chrome** (coin méta) →
  `<dialog>` natif (modal, Échap, focus-trap navigateur, zéro lib) listant les
  définitions des métriques présentes.
- **E3** : panneau latéral « ? » par titre de section (à la Picarones). — Plus
  lourd, redondant avec E1+E2.
- La `GlossarySection` bas-de-page **disparaît** (le YAML + loader restent, deux
  nouveaux consommateurs).

### F. Tables vivantes

- **Tri client** par clic d'en-tête (~40 lignes JS : lire les `<td>` du DOM rendu,
  réordonner les `<tr>` — aucune donnée reconstruite), `aria-sort`, flèches ↕↑↓,
  chip « ordre actif / réinitialiser » (retour à l'ordre manifeste).
- En-têtes : acronyme + flèche + min-méta (`th-acro`/`th-meta` de la cible) +
  définition au survol (E1).
- « Cliquer une ligne ouvre le profil » (lié à D).

### G. Graphes SVG (T2 — actée, concrétisée ici)

Réalistes **avec les données présentes** : dispersion par moteur (bande
min·méd·µ·max depuis `documents`), courbe de calibration (bins du payload),
CER par document trié (profil moteur), composition d'erreurs (taxonomy).
**Pas** d'intervalle de confiance bootstrap : non calculé aujourd'hui — le
graphe IC attendra la stat (étape 4) ; on ne dessine pas ce que le moteur ne
produit pas. Convention d'arrondi fixée à cette tranche (déterminisme).

### H. Strates (composition du corpus, filtres galerie, CER/strate)

**Bloqué par l'enveloppe** : `RunDocumentResult` ne porte aucune métadonnée ;
`CorpusSpec.metadata` existe mais ne descend pas au document dans le résultat.
Extension **petite et légitime** (un champ métadonnées/strate optionnel au niveau
document du résultat) → à faire **avec ses consommateurs** (carte Composition +
chips filtre + CER par strate), comme tranche dédiée. Pas un préalable des autres
chantiers.

### I. Micro-polish transversal

Nombres FR (`1,4 %`, espace fine insécable) — la « i18n des nombres » différée de
3a trouve sa tranche ici ; densités/espacements des cartes alignés sur
`tokens.css` ; états vides soignés par vue ; `prefers-reduced-motion` pour le
scroll ; impression (CSS print : onglets → empilé).

---

## 4. Plan séquencé (chaque tranche : visible, testée, `make ci`)

| Tranche | Contenu | Dépend de | Effet |
|---|---|---|---|
| **U1 — Design system** | A1 (chrome+tabs+méta+exports) · B2 (héros + cartes par vue) · E1+E2 (glossaire contextuel, dépose la section) · typo onglets | rien | le rapport *ressemble* à la cible |
| **U2 — Graphes SVG + verdict qualifié** | G (dispersion · calibration · CER/doc · composition) · **badges de significativité inline** sur le classement de la Vue d'ensemble (D-096) | U1 (cartes où les poser) | les vues *parlent*, le verdict est *qualifié* |
| **U3 — Tables vivantes + profils moteur** | F (tri, survol-définitions) · D (drill-in moteur) | U1, U2 | l'exploration *moteur* |
| **U4 — Documents : galerie-entrée + détail léger** | C (galerie d'abord, toggle ⊞/≡, hash-drill-in, détail données-présentes) | U1 | l'exploration *document* |
| **U5 — Strates** | H (enveloppe + composition + filtres + CER/strate) | U4 (les filtres ont leur galerie) | la dimension *corpus* |
| **T3 (D-094)** | réfs image dans l'enveloppe + vraies vignettes (saveur fichier + budget) | U4 | la galerie devient *réelle* |
| **T4 (D-094)** | fac-similé medium + diff complet borné dans le détail document | T3 | la *preuve visuelle* |

**File unique** : U1 → U2 → U3 → U4 → U5 → T3 → T4 (puis saveurs dossier/IIIF et
volet app web, D-094 §4, à re-prioriser face à l'étape 4 du `PLAN_FIN_MIGRATION.md`
le moment venu). Logique de l'ordre : U1 d'abord parce que tout le reste se pose
*dans* ses cartes et son chrome ; graphes avant drill-ins parce que les profils
moteur (U3) les réutilisent ; documents (U4) avant strates (U5) parce que les
filtres sans galerie-entrée n'ont pas de sens ; les images (T3/T4) closent la
file parce qu'elles seules touchent l'enveloppe.

---

## 5. Garde-fous spécifiques à ce chantier

- **Budget JS global du rapport** : viser ≤ ~600 lignes cumulées (`report.js` +
  tri + drill-ins + exports). Chaque ligne JS *révèle, trie ou navigue* du DOM
  rendu serveur — jamais ne construit du contenu. Si on s'approche du budget,
  on élague avant d'ajouter.
- **Pas de section en avance sur la donnée** (IC bootstrap, strates avant H…).
- **Règle de croissance de l'IA** (D-096) : *un onglet = une question, une
  section = une réponse*. Les familles de métriques de l'étape 4 atterrissent
  dans l'onglet de leur question — jamais un onglet par famille, jamais un
  5ᵉ onglet sans décision explicite.
- **La couche « vue » (B2) est de l'agencement**, pas un second contrat : si un
  compositeur de vue se met à calculer des données, il est au mauvais étage.
- **Sans JS, tout reste lisible** : onglets empilés, tables non triées mais
  complètes, drill-ins dépliés ou accessibles par ancre, dialog glossaire → la
  cible `<details>` de repli. À tester (un test « no-JS markup complet »).
- Déterminisme : tri = runtime client (le HTML livré reste octet-stable) ;
  arrondi SVG fixé ; hash CSP recalculé à chaque évolution de script (mécanisme
  `embedded.py` existant).
