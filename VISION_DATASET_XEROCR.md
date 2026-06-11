# Vision — Banc de corpus XerOCR standardisé sur Hugging Face

> **Statut : direction produit voulue, milestone dédié** (≠ feature différée « au
> cas où »). C'est un **chantier parallèle** au rendu du rapport, avec des
> **prérequis réels** (droits, spec). Journal : `MIGRATION_PLAN.md` D-094.

---

## 1. L'idée

Curer **à l'avance** un ensemble de corpus à vérité-terrain, multi-genres
(**médiéval, presse XIXe, incunables, manuscrits XIXe, imprimés anciens…**),
**standardisés pour XerOCR**, publiés sur **Hugging Face**, de sorte que :

- les **runs soient reproductibles** d'une machine à l'autre (corpus = intrant
  pinné, pas des fichiers locaux qui varient) ;
- les **images soient hébergées** de façon durable (IIIF statique) → les saveurs
  de rapport (cf. `xerocr/reports/DECISION_RAPPORT_INTERACTIF.md`) tombent toutes
  seules ;
- on obtienne un **banc d'essai patrimonial de référence**, multi-sujets — l'effet
  « jeu de données standard » du domaine (HTR-United, ICDAR, CREMMA…).

---

## 2. Pourquoi c'est la bonne direction

| Atout | Détail |
|---|---|
| **Reproductibilité inter-machines** | Un Dataset HF est **git** → chaque révision a un **SHA** → on l'épingle dans `RunManifest`. Le corpus devient un intrant **pinné et citable**. C'est la pièce qui rend l'invariant repro vrai *entre utilisateurs*. |
| **Norme du domaine** | Le benchmark OCR/HTR vit sur des corpus partagés. Un banc XerOCR multi-genres est légitime et différenciant. Importeurs HTR-United/IIIF/Gallica déjà présents. |
| **Hébergement image résolu** | Corpus canonique = images + IIIF statique + manifestes → **références durables par construction**. |
| **Bibliothèque du Space public** | Un visiteur benchmarke contre ces corpus publics **sans rien uploader**, avec des images **légales** à afficher. Résout aussi le corpus de démo du Space. |

---

## 3. « IIIF sur HF » = IIIF **statique** (pas de serveur)

Un serveur IIIF dynamique devrait tourner (→ un Space, écarté). La forme adaptée
à HF est **statique** :

- **Image API Level 0** : tailles pré-générées + `info.json` par image, déposés
  en fichiers statiques (servis par le CDN du Dataset, ne dort jamais).
- **Presentation API** : les **manifestes** (décrivant un objet/corpus : pages,
  images, métadonnées) sont **du JSON** → idéaux pour un Dataset.

Pas de deep-zoom (décision rapport : zoom medium + pan/zoom léger) → **pas de
pyramide de tuiles** : on se limite aux tailles `vignette` + `medium`. Léger.

---

## 4. Le point dur : les **droits**

Les fac-similés patrimoniaux ne sont **souvent pas redistribuables**. Règle :

- **Sources ouvertes** (domaine public / CC : écosystème HTR-United, CREMMA,
  numérisations libres) → **héberger les dérivés** sur HF (repro forte, SHA pinné).
- **Sources restreintes** → héberger **seulement la GT + un manifeste qui
  *référence* le IIIF de l'institution** (on pointe Gallica, on ne recopie pas).
  Repro plus faible (le distant peut changer) → réservé au hors-canon.

La curation se **scope donc au légalement diffusable** : c'est un coût de
diligence réel, pas juste technique.

---

## 5. Le vrai travail de design : la **spec de standardisation**

« Adapté à XerOCR » = définir un **layout canonique** du Dataset :

- GT (ALTO / PAGE / texte), références image/IIIF, métadonnées de **strate**
  (genre, siècle, écriture), versioning ;
- **aligné sur les types `domain`** (`Corpus`/`Document`/`Artifact`/
  `EvaluationView`) — sinon on crée un second format incompatible ;
- un **importeur** XerOCR qui lit ce layout depuis HF (revision SHA → `RunManifest`).

C'est là qu'est l'effort. Bien fait → tout l'aval est propre.

---

## 6. Prérequis & séquencement

- **Socle commun, indépendant, à poser d'abord** (déjà acté côté rapport) : le
  `RunResult`/modèle corpus portent des **références** image (URL IIIF / chemin),
  pas les octets. Ce socle rend ce chantier possible **sans s'enfermer**.
- **Ce milestone vient après** ce socle, en parallèle des saveurs de rapport
  hors-ligne. Ordre interne → externe, par tranches.
- **Prérequis** : (1) tri des droits par source ; (2) spec de layout validée
  contre `domain` ; (3) pipeline de publication (génération dérivés + manifestes
  + upload `huggingface_hub`, token write) ; (4) importeur de lecture.

---

## 7. Limites assumées

- **Public + en ligne** : ne marche proprement que pour des corpus **publics**
  (un Dataset privé exige un token → impossible dans un rapport partagé). La
  saveur **hors-ligne** (fichier/dossier) reste le défaut pour le local/privé.
- Repro **forte** pour le sous-ensemble **ouvert hébergé+pinné** ; **faible** pour
  les images référencées en IIIF externe.
