# ANALYSE — Graphiques didactiques du rapport XerOCR

> **Design cible (périssable, PROVISOIRE — à confirmer au build).** Catalogue
> exhaustif des graphiques/tableaux *didactiques* envisageables pour le rapport,
> chacun rattaché à **sa donnée réelle** (payload existant ou calcul à ajouter).
> Objectif produit : **juger les moteurs sur la matière première** — voir les
> *mots* et *symboles* réellement ratés, posés sur le graphique — sans passer
> uniquement par des chiffres.
>
> Lu avant rédaction : `CLAUDE.md`, `xerocr/reports/DECISION_RAPPORT_INTERACTIF.md`
> (D-094), `xerocr/evaluation/analysis.py` (les 16 payloads + champs verbatim),
> `xerocr/reports/svg.py` (socle SVG existant), `MIGRATION_PLAN.md` (roll-up).

---

## 0. Cadre & principes

**Didactique = lisible d'un coup d'œil, et ancré dans la matière.** Deux registres :
1. **Quantitatif visuel** — donner une *forme* à des chiffres déjà calculés
   (profil d'erreurs, divergence, coût/qualité). Rend comparables des nombres
   qu'une table noie.
2. **Qualitatif / matière première** — poser sur le graphique les **vrais mots
   et symboles** (le mot raté, le glyphe perdu, la confusion `ſ→f`). On juge à
   l'œil, la matière *est* la donnée.

**Contraintes d'enveloppe (D-094 — non négociables) :** SVG **inline** serveur,
**autonome/hors-ligne**, **octet-stable** (coordonnées arrondies, cf. `svg.py`),
**zéro JS lourd** (un seul script mince CSP-hashé), **pas de SPA**, **pas de
Chart.js**. Tout graphe est une *fonction pure et auditable* du `RunResult`
(anti-hallucination : aucun nombre/mot inventé, tout vient des payloads).

**Deux axes.** Le socle (`svg.py`) existe (4 formes : dispersion, barres, barre
composée, courbe de calibration). On **étend le vocabulaire un graphe à la fois**
(helper SVG + câblage de section + tests valeurs-main + golden de markup), jamais
en masse.

**Statut de la donnée — le point clé.** La **quasi-totalité** des graphiques
ci-dessous se nourrit de payloads **déjà calculés et testés**. **Un seul** besoin
de **calcul nouveau** : la *matrice mots × moteurs* (§1). Et beaucoup de
**matière verbatim est déjà collectée** (cf. §2) — il ne lui manque que sa mise
en image.

---

## 1. La carte des mots — cross-moteurs, regroupée *(calcul nouveau — pièce maîtresse)*

**La demande.** Voir les **mots** que les moteurs ratent : combien de fois, par
moteur, avec **croisements** (quels mots plusieurs moteurs ratent vs un seul) et
**regroupements**. Juger sur la matière.

**C'est possible — et l'alignement nécessaire existe déjà.** `textual_fidelity`
tokenise en Unicode (`\w`) et **aligne mot-à-mot** (`difflib.SequenceMatcher`)
pour la modernisation. On **réutilise cette mécanique** pour un nouvel angle.

### Nouvelle analyse couche 3 : `WordErrorCollector` → `WordErrorPayload`
- **Collecte** (pendant la passe 1, comme les autres collecteurs) : pour chaque
  `(pipeline, document)`, aligner GT↔hyp au mot ; pour chaque **mot GT non
  restitué** (tag `replace`/`delete` de l'alignement), incrémenter
  `errors[mot_gt][pipeline]`. On peut garder la **forme produite** dominante
  (ce que le moteur a mis à la place) — la matière de la confusion mot.
- **`build()` cross-pipelines** (pattern `inter_engine`) : cross-tabuler →
  par mot GT, le compte d'erreurs **par moteur** + des **signatures de
  regroupement** :
  - `universal` — *tous* les moteurs ratent le mot (difficulté de la **matière**) ;
  - `engine_specific` — *un seul* moteur rate (faiblesse **moteur**) ;
  - `partial` — un sous-ensemble (recoupement partiel).
- **Payload** (cap explicite, ex. top 50 mots par fréquence d'erreur totale) :
  ```
  WordErrorPayload(kind="word_errors",
    words: tuple[WordError]  # {word, total_errors, per_engine:{engine:count},
                             #  top_variant:{engine:forme_produite}, group}
    groups: {universal:[...], engine_specific:{engine:[...]}, partial:[...]})
  ```
- **Conventions / honnêteté** : appariement dépend de la **normalisation de la
  vue** (documenté) ; fusion/scission de mots = limite connue (héritée de
  l'alignement) ; cap d'échantillon explicite ; tri déterministe ; GT vide → mot
  ignoré. **Aucune invention** : les mots sont *verbatim* de la GT, les variantes
  *verbatim* de la sortie.

### Graphiques (lisent ce payload — la matière est affichée)
| Graphique | Forme | Ce qu'on lit à l'œil |
|---|---|---|
| **Matrice mots × moteurs** | heatmap : lignes = mots **verbatim**, colonnes = moteurs, case teintée = nb d'erreurs (triable, regroupée par signature) | « *prologve* : A rate 8×, B 0, C 2 » — qui bute sur quoi |
| **Mot → mini-barres par moteur** | liste de mots, chacun avec une micro-barre par moteur | classement des mots les plus durs, comparaison directe |
| **Recouvrement inter-moteurs** | diagramme d'ensembles (UpSet/Venn) sur les mots ratés | les mots que *tous* ratent (matière dure) vs propres à un moteur |
| **Mot → variante produite** | par mot dur, le glyphe/forme que chaque moteur a produit | la *nature* de l'erreur, lisible (`maistre`→`maître`/`maistrc`) |

> **Niveau symbole, même principe.** La même logique au grain caractère/abréviation
> est **déjà servie** par `diagnostics.confusions` (paires `attendu→produit`) et
> `philology`/`roman` (les signes) — il ne manque que la *mise en image* (§2, §3).

---

## 2. La matière déjà collectée (verbatim) — il ne manque que l'image

XerOCR collecte déjà beaucoup de **matière première** par payload. Aujourd'hui
elle vit dans des **tables** ; la rendre **graphique/groupée** est du rendu pur
(zéro calcul nouveau) :

| Matière verbatim | Champ (payload) | Mise en image proposée |
|---|---|---|
| Pires lignes (réf vs hyp) | `diagnostics.worst_lines` (`reference`, `hypothesis`) | diff coloré aligné, trié par CER |
| Mots OCR-justes cassés par le LLM | `correction.over_normalized_samples` (`reference`→`corrected`) | flèches `mot→forme` (sur-normalisation) |
| Régressions de correction | `correction.worst_regressions` | barres divergentes par document |
| Tokens rares manqués | `textual_fidelity.missed` | nuage/liste des noms propres perdus |
| Modernisation lexicale | `textual_fidelity.modernization` (`token`→`variants`) | flux token → variantes (taille = compte) |
| Séquences perdues | `structured_data.lost` (formes verbatim) | liste par catégorie (dates/folios/montants) |
| Numéraux romains perdus | `roman.lost_samples` | liste + statut (converti/perdu) |
| Entités manquées / hallucinées | `ner.missed` / `ner.hallucinated` (`text`) | deux colonnes : ce qui disparaît / ce qui est inventé |
| Signes philologiques | `philology` (le `sign`) | le **glyphe** + barre de préservation |
| Textes complets des pires docs | `document_texts` (`reference` + `hypotheses`) | diff pleine page (déjà en UI) |

---

## 3. Catalogue complet — « tous les tableaux possibles »

`E` = données **existantes** (payload livré) · `N` = **calcul nouveau** ·
`✓svg` = socle `svg.py` déjà présent. Onglets : Ov (vue d'ensemble) · Mo (par
moteur) · Doc (par document) · Cr (croisements).

| # | Graphique / tableau | Enseigne (didactique) | Source | Matière mots/symboles | Statut | Onglet |
|---|---|---|---|---|---|---|
| 1 | **Matrice mots × moteurs** | qui rate quels mots, croisements | `word_errors` | **oui (mots)** | **N** | Cr |
| 2 | Recouvrement inter-moteurs (mots) | mots durs partagés vs spécifiques | `word_errors` | oui | N | Cr |
| 3 | Mot → variante produite | la *nature* de l'erreur mot | `word_errors` | oui | N | Cr |
| 4 | **Carte des erreurs** (treemap) | la *forme* du budget d'erreurs | `taxonomy` (+`diagnostics`) | classes/paires | E | Mo |
| 5 | **Profil taxonomique** par moteur | A diacritique-lourd, B segmentation | `taxonomy` | — | E | Mo |
| 6 | **Matrice de divergence JS** (heatmap) | moteurs qui se trompent *différemment* | `inter_engine` | — | E | Cr |
| 7 | Oracle / complémentarité | gain théorique d'un ensemble | `inter_engine` | — | E | Cr |
| 8 | **Flux de confusion** `attendu→produit` | directionnalité (`ſ→f` vs `f→ſ`) | `diagnostics.confusions` | **oui (glyphes)** | E | Mo |
| 9 | Pires lignes (diff verbatim) | *où* ça casse, texte à l'appui | `diagnostics.worst_lines` | oui | E | Doc |
| 10 | Documents les plus durs | quels docs résistent à tous | `diagnostics.hardest_documents` | — | E | Doc |
| 11 | **Nuage coût ↔ qualité** + Pareto | le choix moteur (€/CER) | `economics` | — | E | Mo |
| 12 | Coût marginal €/erreur évitée | le surcoût en vaut-il la peine | `economics.marginal` | — | E | Mo |
| 13 | Débit effectif (pages/h corrigé) | vitesse réelle post-correction | `economics` | — | E | Mo |
| 14 | **Bilan de correction** (barre triplet) | l'étage LLM aide-t-il, de combien | `correction` | — | E | Mo |
| 15 | Flux corrigées/introduites/conservées | l'absorption d'erreurs du LLM | `correction` | tokens | E | Mo |
| 16 | Sur-normalisation `mot→forme` | le LLM casse des mots justes | `correction.over_normalized_samples` | **oui** | E | Mo |
| 17 | **Flux de modernisation** | formes historiques réécrites | `textual_fidelity.modernization` | **oui (tokens)** | E | Mo |
| 18 | Tokens rares manqués | noms propres perdus (prosopo) | `textual_fidelity.missed` | oui | E | Mo |
| 19 | **Préservation philologique** (signes) | abréviations/ligatures tenues | `philology` | **oui (glyphes)** | E | Mo |
| 20 | Romains : 5 statuts + perdus | la valeur a-t-elle survécu | `roman` | oui | E | Mo |
| 21 | Séquences restituées par catégorie | dates/folios/montants tenus | `structured_data` | oui (perdus) | E | Mo |
| 22 | **Entités : P/R/F + manquées/hallucinées** | survie des noms propres | `ner` | **oui (entités)** | E | Mo |
| 23 | Courbe de calibration (+ écart/bin) | le moteur sait-il qu'il doute | `calibration` | — | E ✓svg | Mo |
| 24 | **Heatmap positionnelle des lignes** | décrochage haut→bas de page | `lines.heatmap` | — | E | Doc |
| 25 | Distribution CER par ligne (percentiles) | erreurs uniformes vs concentrées | `lines` | — | E | Doc |
| 26 | Conformité HIPE : deltas de norm. | part casse/ponct./mappings | `conformity` | — | E | Mo |
| 27 | Classement + dispersion par moteur | verdict + fiabilité (min·méd·max) | scalaires | — | E ✓svg | Mo |
| 28 | Composition du corpus par strate | de quoi le corpus est fait | strates | — | E ✓svg | Ov |
| 29 | **Qualité d'image : distribution paliers** | combien de scans bons/moyens/faibles | `image_quality` (4d.1) | — | E | Doc |
| 30 | **Scatter qualité d'image ↔ CER** | « le moteur ou le **scan** ? » | `image_quality` × CER par doc | — | E (jointure) | Doc |

---

## 4. Ce qui demande un calcul nouveau (le seul ajout d'enveloppe)

- **`WordErrorPayload` + `WordErrorCollector`** (#1-3) — matrice mots × moteurs +
  regroupements. Réutilise l'alignement mot de `textual_fidelity` ; pattern
  cross-pipeline de `inter_engine`. **Tout le reste (#4-30) = renderers SVG sur
  payloads existants** (+ une jointure triviale pour #30).

> Ergo : l'enveloppe couche 3 est quasi suffisante. Le gros du chantier est en
> **couche 7** (vocabulaire SVG), incrémental, à faible risque.

---

## 5. Séquencement proposé (PROVISOIRE)

Chaque tranche = un (ou deux) graphique(s), livré entièrement : helper `svg.py`
+ section + tests valeurs-main + golden de markup + **libellés bilingues FR/EN
d'emblée** (les graphes portent peu de texte — autant ne pas repasser à l'i18n).

| Ordre | Tranche | Pourquoi |
|---|---|---|
| 1 | **Carte des mots** (#1, puis #2-3) | la demande centrale ; introduit `word_errors` (le seul calcul neuf) + montre la matière |
| 2 | **Carte d'erreurs + profil taxonomique** (#4, #5) | la *forme* des erreurs, comparatif moteurs — data prête, fort rendement |
| 3 | **Matière verbatim mise en image** (#8, #16, #17, #19, #22) | confusions/sur-normalisation/modernisation/signes/entités — « voir les symboles » |
| 4 | **Décision** (#11 coût↔qualité, #14 bilan correction) | les images de choix moteur / valeur du LLM |
| 5 | **Divergence + complémentarité** (#6, #7) | croisements quantitatifs |
| 6 | **Qualité ↔ CER** (#30) + heatmap lignes SVG (#24) | donne sa pleine valeur à 4d.1 ; structure |

> Reste hors périmètre (décision actée) : le **CDD/diagramme de différence
> critique** de Picarones (post-hoc Nemenyi) — jugé **opaque/peu didactique** ;
> la donnée `inference` reste disponible mais ne sera pas mise en diagramme.

---

*Référence : design cible de la couche 7, à confirmer au build (chaque tranche
fige sa forme et ses clés). Enveloppe couche 3 : un seul ajout (`word_errors`).
Contraintes D-094 tenues. `MIGRATION_PLAN.md` indexe ; ce document détaille.*
