# Analyse — vue document du rapport (refonte)

Guide durable de la refonte de la vue document (détail au clic d'une carte de
galerie). Établi après revue de la vue document de Picarones (lecture seule,
`../Picarones/picarones/reports/html/templates/view_document.html` +
`_styles.css` + `_app.js`).

## Constat

La vue document de Cinoc empilait des blocs sans **logique de présentation** :
image à taille variable (le layout saute d'un doc à l'autre), colonnes GT/sortie
non alignées en police dense, graphiques peu pertinents. Picarones — UI sobre
mais **lisible** — repose sur trois cartes nettes : transcription, distribution
par ligne, hallucinations.

## Cible (ordre de présentation, haut → bas)

1. **En-tête** : identifiant + CER par moteur (compact).
2. **Fac-similé** : boîte à **hauteur fixe**, `object-fit:contain`, zoomable/pan
   (ne saute plus entre documents).
3. **Transcription GT | sortie** : **grille 2 colonnes égales**, chaque colonne
   une **carte bordée** (en-tête libellé + badge CER) ; corps **serif**,
   `line-height:1.8`, `max-height` scrollable, `white-space:pre-wrap`. Sélecteur
   de moteur. Diff caractère conservé (suppression = fond doux, sans barré).
4. **Distribution des erreurs par ligne** (riche) : carte thermique de position
   (début→fin) + **percentiles CER** (p50→p99) + badges (Gini, n lignes,
   % lignes au-dessus de seuils). Les données par ligne existent déjà
   (`DocumentLinesCollector`) ; le rendu est enrichi.
5. **Analyse des hallucinations** par moteur : ancrage, ratio de longueur,
   insertion nette, comptes de mots GT/sortie, **+ les blocs hallucinés
   affichés**. À porter de `hallucination.py` (Cinoc n'a que le scalaire).
6. **Qualité d'image** : **une ligne indicative** (les mesures sont réelles mais
   les seuils sont des conventions non calibrées — pas un bloc de jauges qui
   suggère une précision absente).

## Décisions

- **Taxonomie catégorielle** (casse/diacritiques/…/`other`) : reste un outil de
  **niveau corpus** (agrégée, `other` n'y domine pas). **Pas** dans la vue
  document : sur un seul document `other` écrase tout, et l'exclure casserait la
  validité (elle prétendrait l'exhaustivité). On ne la tronque jamais.
- **Composition suppression / insertion / substitution** : **exhaustive**
  (∑ = 100 %, aucun `other`) → décomposition honnête de la nature des erreurs ;
  s'articule avec l'insertion nette des hallucinations (ne pas doublonner).
- Les graphiques restent **déterministes**, lecture seule du `RunResult`, aucun
  texte généré (anti-hallucination du rapport).

## Tranches

- **P1** — cadre lisible : boîte image fixe + transcription 2 colonnes
  bordées/serif + hiérarchie en cartes.
- **P2b** — analyse des hallucinations par document (collecteur + payload + rendu).
- **P2a** — distribution par ligne riche (percentiles + Gini + seuils + heatmap).
