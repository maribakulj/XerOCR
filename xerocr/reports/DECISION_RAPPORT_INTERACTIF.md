# Décision — Rapport interactif **et** autonome (images + interactivité)

> **Statut : décision actée** (conversation de design, juin 2026). Les **formes
> exactes** (noms de champs, budgets chiffrés) sont **à confirmer au build** —
> seul le *cadre* est figé ici. Journal : `MIGRATION_PLAN.md` D-094.

Ce document fige l'architecture du **rapport HTML** de XerOCR après le constat
que le rapport plat actuel (sections empilées + sommaire à ancres) est **loin**
de la cible (onglets, galerie à vraies vignettes, drill-in document, graphes).

---

## 1. Principe : autonome ≠ statique

L'erreur à ne pas commettre : croire qu'« autonome » impose « statique ». Un
fichier HTML autoportant peut être **interactif hors-ligne** (Picarones le fait ;
XerOCR le fait déjà à petite échelle — widget compare, nav clavier, scripts
inline épinglés CSP). Le piège n'est **pas** l'interactivité — c'est la **manière**
de Picarones : ~3 400 lignes de JS écrit main + Chart.js vendoré + un data-layer
qui ré-agrège.

**On vise l'interactivité, mais DISCIPLINÉE** (≠ la SPA Picarones) :

1. **Une seule « île de données »** : le `RunResult` embarqué tel quel
   (`<script type="application/json">` inerte). Unique source en navigateur —
   **aucun data-layer qui recalcule**.
2. **Enrichissement progressif** : le serveur rend **tout** le contenu en HTML
   (le `Protocol Section` unique reste). Le JS **navigue** (montre/cache/scrolle
   des panneaux *déjà rendus*), il ne **construit** rien. Onglets = bascule de
   visibilité ; drill-in = révéler un panneau déjà dans le DOM. → JS mince
   (~200-400 lignes), dégradé propre sans JS.
3. **Un seul petit script, épinglé CSP** (mécanisme `embedded.py` existant :
   sha256 sur `/reports/`). Autonome, déterministe (script statique → octets
   stables).
4. **Graphes en SVG inline** rendus **côté serveur** depuis les données.
   **Pas de Chart.js** (cf. §6).

> ⚠️ Ce cadre **nuance une décision documentée** (`CLAUDE.md §8`, analyse
> couche 7 : anti « rapport-application »). On ne revient PAS à la SPA Picarones ;
> on passe de « zéro interactivité riche » à « interactivité **disciplinée** ».
> Revirement assumé et consigné (journal D-094) — pas un passage en force.

---

## 2. Images : le `RunResult` porte des **références**, jamais les octets

Invariant : le `RunResult` canonique reste **maigre et hashable** (déterminisme,
historique, repro). Il porte, par document, une **référence** d'image (URL IIIF
ou chemin relatif dans le corpus store), **jamais les octets**. Les images sont
un **intrant au moment du rendu**, pas un champ du résultat.

Conséquence : on peut générer **n'importe quelle saveur** de rapport plus tard,
sans re-run, tant que la source image est joignable.

---

## 3. Stratégie image, décidée **par document** au rendu

| Le doc a… | Stratégie | Coût | Hors-ligne |
|---|---|---|---|
| une **URL IIIF** | référencer IIIF à la bonne taille (`…/full/250,/…`) | ~nul | ❌ réseau |
| une **image locale**, mode dossier | dérivés (vignette + medium) dans `report-assets/` | génération + disque | ✅ |
| une **image locale**, mode fichier | vignette embarquée (250 px / 64 px si gros + budget) | poids HTML | ✅ |
| **rien** | aperçu CSS synthétique | nul | ✅ |

On **ne sert jamais l'original brut** dans une grille (fac-similés patrimoniaux
= plusieurs Mo). En mode dossier/local on génère des **dérivés** : vignette
~250-400 px (grille) + medium ~1600-2048 px (drill-in). L'original n'est gardé
que si le zoom pixel l'exige (cf. §7 — il ne l'exige pas).

---

## 4. Saveurs de rapport (un `RunResult` → plusieurs sorties, choisies à la génération)

| Saveur | Images | Hors-ligne | Scale | Idéal pour |
|---|---|---|---|---|
| **Fichier unique** | vignettes embarquées (250/64 px + budget) | ✅ | plafonné | partager un verdict |
| **Dossier** | dérivés dans `report-assets/` | ✅ (comme dossier) | milliers | archive locale d'un gros run |
| **Réfs IIIF / HF** | `<img>` vers URLs durables (IIIF statique / dataset) | ❌ | ∞ | rapport-lien riche, durable |
| **Servi (app web)** | images servies à la demande | ❌ | ∞ | exploration en ligne, le plus riche |

> **Abandonné** : servir les images depuis l'app-Space comme socle d'un fichier
> « autonome » (FS éphémère + free-tier qui dort → fragile ; rend le fichier
> dépendant du Space). L'app web sert pour la saveur **« servie »**, pas pour
> adosser un fichier prétendu autonome.

---

## 5. Budgets & plafonds (le vrai garde-fou d'échelle)

Le coût galerie + drill-in est en **O(nombre de docs)** ; le « verdict »
(agrégats, graphes, croisements) est en **O(moteurs × métriques)** — négligeable.
Donc on **borne** la partie par-document, par un **budget d'octets dur** (≠ simple
comptage) :

- **Galerie** : toutes les cartes (vignette lazy + CER/badges). Tient à des
  milliers tant qu'on **ne pré-rend pas** les panneaux de drill-in.
- **Drill-in texte « page complète »** (diff GT ↔ sortie OCR) : **plafonné par
  budget** (~2-3 MB → **~100-200 pages moyennes**, moins pour de la presse
  dense), **pires-d'abord**. Au-delà → « voir le texte complet dans l'app web ».
- **Choix de mode au lancement** (selon nombre de docs) **+ application du budget
  au rendu** (le poids réel dépend des vraies images/textes). Déterministe :
  même corpus → même profil → même rapport.

Pourquoi un budget plutôt qu'un comptage : un corpus de 300 docs à gros
fac-similés peut peser plus qu'un de 1500 docs en texte court. Le budget garantit
**le fichier ne dépasse jamais X MB, point.**

`file://` interdit `fetch` → en hors-ligne on **ne peut pas** charger le texte à
la demande : d'où le plafond embarqué + le renvoi à l'app web (servie → `fetch`
autorisé → tout en lazy, zéro mur).

---

## 6. Graphes : SVG inline, **pas Chart.js**

| | SVG inline (retenu) | Chart.js (rejeté) |
|---|---|---|
| Déterminisme | ✅ markup, octet-stable (arrondi flottants fixé) | ❌ canvas runtime, non reproductible |
| Autonomie | ✅ zéro lib | ❌ blob ~200 KB vendoré/rapport |
| Accessibilité | ✅ vrai DOM, `<title>`/aria, sélectionnable | ❌ pavé de pixels opaque |
| Besoin réel | dispersion, IC, courbe calibration, donut = formes simples | sur-dimensionné |

Le SVG nous **donne** nos invariants là où Chart.js nous les **coûte**.

---

## 7. Onglets, drill-in, zoom

- **Onglets** : 4 (Vue d'ensemble / Par moteur / Par document / Croisements),
  par enrichissement progressif (panneaux rendus serveur, JS bascule la
  visibilité).
- **Drill-in document** : clic sur une vignette → fac-similé (medium) + diff
  GT ↔ sortie OCR + CER par moteur + clic moteur pour changer le diff. Borné
  hors-ligne (§5), complet en app web.
- **Zoom** : image **medium ~1600-2048 px** + pan/zoom CSS léger. **Pas de
  deep-zoom** (pas de pyramide de tuiles, pas de viewer type OpenSeadragon). À
  1600-2048 px on lit chaque caractère — suffisant pour l'inspection d'erreur
  OCR. Décision nette, pas un palier différé.

---

## 8. Correction d'un record antérieur (D-086)

D-086 justifiait la « galerie synthétique » par « Picarones n'embarque pas les
images par défaut ». **C'est une mauvaise lecture** : le code Picarones affiche
une **vraie vignette `<img>` dès qu'une image est dispo** (« cas standard pour
`picarones demo` »), le synthétique n'étant que le **fallback**. XerOCR avait
donc reproduit le **mode dégradé** et l'avait pris pour le design.

**Cible corrigée** : galerie à **vraies vignettes** ; synthétique = **dégradé
gracieux** (pas de Pillow, pas d'image, ou budget dépassé).

---

## 9. Frontière fichier ↔ app web (récap)

| | Fichier autonome (uni/dossier) | App web servie |
|---|---|---|
| Galerie | vignettes (embarquées/dérivées), bornée par budget | complète, paginée, lazy |
| Drill-in texte | plafonné (~100-200 pages) | complet (fetch à la demande) |
| Images | embarquées / `report-assets/` / réfs IIIF | servies à la demande |
| Réseau | hors-ligne (sauf saveur réfs IIIF) | en ligne |

---

## 10. Implications d'enveloppe (à concevoir au build)

- **`domain`/`evaluation`** : `RunDocumentResult` (ou un index parallèle) gagne
  une **référence image optionnelle** (URL IIIF | chemin corpus-relatif). Forme
  exacte à confirmer — surtout **pas** d'octets dans `RunResult`.
- **`reports`** : générateur paramétré par **saveur** + un **intrant images**
  (mapping doc → source) ; SVG charts ; île de données ; un script mince
  CSP-hashé ; rendu **par onglets** (sections regroupées en 4).
- **`app`/`interfaces`** : la saveur « servie » expose galerie paginée + drill-in
  à la demande (l'app web n'a pas la contrainte d'autonomie).

L'ordre reste **interne → externe**, par **tranches verticales** (squelette
d'abord). Première tranche à cadrer séparément.
