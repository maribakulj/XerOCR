# `corpus/` — corpus lourds, avec images et structure

Arrivés de [`saknussemm`](https://github.com/maribakulj/saknussemm) le
2026-08-16, où ils servaient à mesurer une bibliothèque de post-correction
et pesaient 43 Mo dans un dépôt qui n'a plus vocation à contenir que du
code publiable.

Ils ne sont **pas** des fixtures de test : la suite ne les lit pas, et rien
ici ne doit se mettre à en dépendre pour tourner. Ce sont des **corpus de
campagne** — la matière des runs réels, à référencer par un manifeste.

## `37-GT-BNL/` — et pourquoi il change quelque chose

37 pages appariées `NNNN.xml` + `NNNN.png`. Presse luxembourgeoise du 19ᵉ
siècle, vérité terrain de la **Bibliothèque nationale du Luxembourg**.

- **ALTO v4**, `MeasurementUnit = mm10` (dixièmes de millimètre, **pas** des
  pixels). Scans **300 DPI**, donc XML → pixels est un facteur uniforme
  `dpi/254 ≈ 1,1811`, vérifié sur les 37 pages.
- Le `CONTENT` est la **transcription humaine** (`CC="00"`), pas une sortie
  d'OCR.
- **Licence : CC0 / domaine public**, par déclaration de la BnL elle-même
  (« As part of BnL's AI strategy, we provide the ground truth data that
  falls into the public domain »). Rediffusion libre.

**Ce corpus est le même que `tests/fixtures/reference_corpus/bnl_mini/`, à
un autre niveau.** Vérifié avant de le verser : **29 identifiants communs**,
et le texte de `<id>.gt.txt` se retrouve mot pour mot dans le `CONTENT` de
`<id>.xml`. `bnl_mini` porte la projection **texte** de ces pages, plus cinq
sorties OCR figées de qualités échelonnées ; ce dossier apporte ce qui lui
manquait : **la structure et l'image**.

Concrètement, ça débloque sur le corpus déjà mesuré ici :

- les pipelines **VLM** et **hybrides**, qui ont besoin de l'image ;
- `region_cer` et toute évaluation qui apparie par identifiant, qui ont
  besoin du layout ;
- une vérité terrain `LAYOUT` déclarable, que l'enveloppe sait déjà charger
  (`evaluation/representations.py`) mais qu'aucun importeur ne produit ;
- et l'évaluation d'un correcteur **préservant la structure**, qui est
  précisément ce que cette plateforme ne sait pas encore mesurer.

## `BnF-bpt6k3265015q/`

Un feuillet de presse française du 19ᵉ (`X0000002`), ALTO + JPEG, **domaine
public**, librement téléchargeable depuis Gallica.

Nuance consignée plutôt qu'ignorée : les conditions de la BnF portent sur la
*reproduction numérique* et distinguent réutilisation non commerciale
(libre) de commerciale (sous licence). Un usage de corpus de mesure relève
de la première.

⚠️ **Ce feuillet porte une césure inter-pages réelle**, mesurée le
2026-08-16 : sa dernière ligne finit sur `« …le roi monte sur la pla- »`, et
la suite (`te-forme`) est sur le feuillet 3. C'est le seul cas de ce type
identifié dans les corpus des deux dépôts, et le chemin inter-pages n'est
mesuré par aucun run à ce jour — ni ici, où la notion de document
multi-pages n'existe pas encore.

## Ce que ces dossiers ne doivent pas devenir

Une dépendance de la suite. `make check-fast` doit rester vert sur une
machine qui ne les a pas — s'ils deviennent nécessaires à un test, c'est
qu'il fallait une fixture, et une fixture vit dans `tests/fixtures/`.
