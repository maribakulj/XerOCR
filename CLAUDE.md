# CLAUDE.md — XerOCR

Réécriture propre de **Picarones** (plateforme de benchmark OCR/HTR/VLM pour
documents patrimoniaux) sous le nouveau nom **XerOCR**. Ce fichier est le
contrat de travail de toute conversation de migration. **Le lire en entier
avant d'écrire la moindre ligne.**

---

## 0. Statut actuel

- Dépôt vierge, branche de travail : `claude/focused-gates-6737Q`.
- Échafaudage posé : `xerocr/` avec 8 packages (un `__init__.py` vide par couche).
- Couche 1 (`domain`) : plan de migration prêt dans
  [`xerocr/domain/MIGRATION_COUCHE_1.md`](xerocr/domain/MIGRATION_COUCHE_1.md).
- Aucune couche encore implémentée.

---

## 1. Ce qu'est XerOCR

Un banc d'essai **déterministe et reproductible** pour comparer des pipelines de
transcription (OCR, HTR, VLM, OCR+LLM) sur des corpus à vérité-terrain
patrimoniaux, et produire un **verdict factuel chiffré** (métriques + tests
statistiques) sous forme d'un rapport HTML autonome.

XerOCR n'est PAS un fork. C'est une réécriture qui **recopie le noyau métier
sain** de Picarones et **abandonne sa dette**. Picarones est disponible en
lecture seule comme source de référence à porter (`../Picarones/`).

---

## 2. Principe directeur — les DEUX axes

C'est la règle la plus importante du projet. Ce qui a alourdi Picarones, ce
n'est **pas** son architecture (saine), c'est sa **surface fonctionnelle** qui a
enflé sans élagage, plus des shims de compatibilité traînés. La protection n'est
ni « tout prévoir d'avance » ni « partir petit et grossir », mais de séparer
strictement deux axes :

| Axe | Quand | Règle |
|---|---|---|
| **Architecture / contrats** (l'enveloppe) | **Dimensionnée pour le scope COMPLET, dès maintenant** | Les frontières des 8 couches, les types pivots (`Artifact`, `PipelineSpec`, `RunResult`, `EvaluationView`) et les points d'extension réels sont conçus pour porter *toutes* les features envisagées — même si on n'en remplit qu'une au début. Ex : `RunResult` doit pouvoir contenir taxonomy/NER/calibration dès sa conception, même si la v1 ne calcule qu'un CER. |
| **Surface fonctionnelle** (le contenu) | **Implémentée incrémentalement et minimalement** | Adapters, métriques, renderers, importers : ajoutés un par un, entièrement, dans un budget, en élaguant. Jamais en masse, jamais « au cas où ». |

> Analogie : on coule des fondations dimensionnées pour 3 étages (axe 1), mais on
> finit et on meuble un étage à la fois (axe 2). Implémenter toute la surface
> d'office reproduit le volume de Picarones **et** ajoute du risque spéculatif
> (cf. `BaseModule`, supprimé précisément pour ça).

---

## 3. Architecture — 8 couches concentriques

```
domain ← formats ← evaluation ← pipeline ← adapters ← app ← reports ← interfaces
(interne)                                                            (externe)
```

**Règle d'import absolue** : une couche n'importe **que** des couches plus
internes qu'elle. Jamais l'inverse. Vérifiée mécaniquement par les tests
d'architecture (à activer dès le premier commit de code).

Conséquence opérationnelle : on construit **toujours de l'intérieur vers
l'extérieur**. Dans ce sens, chaque couche écrite ne dépend que de couches déjà
terminées — aucun blocage de dépendance vers l'avant n'est possible.

Whitelist externe de `evaluation/` (rappel Picarones) : `PIL, annotated_types,
jiwer, numpy, pydantic, rapidfuzz, scipy, spacy, typing_extensions, yaml`. Toute
lib OCR/LLM (`pytesseract`, `mistralai`, `azure`, `google`, `pero_ocr`…) vit en
`adapters/`.

### Extensibilité par modules tiers (EXIGENCE D'ENVELOPPE, axe 1)

Brancher facilement un module tiers — un YOLO de HuggingFace, un module Python
développé en local — est un **objectif central du produit**, pas une option.
C'est donc dimensionné dès le départ (≠ la décision initiale de supprimer
`BaseModule`, qui supposait à tort que c'était spéculatif). Conception en
3 briques, à concevoir maintenant avec 2-3 implémentations de référence
seulement (le reste incrémental) :

1. **Contrat de module exécutable (`Protocol`)** — toute brique (segmenteur,
   OCR, VLM, post-correcteur, constructeur d'ALTO) implémente la même forme :
   `name`, `version` (reproductibilité), `input_types`/`output_types`, et
   `execute(inputs typés, params, contexte d'exécution) → outputs typés`. **Un
   seul contrat, implémenté directement** (≠ Picarones qui emballait
   `BaseOCRAdapter` dans `BaseModule`).
   **⚠️ Placement : couche `pipeline` (4), PAS `domain`.** Le contrat porte des
   concerns d'exécution (deadline, annulation via `RunControl`) qui sont des
   types de couche 4 ; un `Protocol` en `domain` qui les référencerait violerait
   le sens des dépendances. La couche `domain` ne garde que le **déclaratif** :
   `PipelineStep` (nomme l'`adapter_name` + ses `input_types`/`output_types`) et
   `ArtifactType` — ça suffit à décrire un module dans une spec.
2. **Registre + factory** — la spec YAML référence un `adapter_name` (string),
   résolu au runtime. Couches `app`/`adapters`.
3. **Découverte de plugins** (absente de Picarones) — **entry-points Python**
   (`xerocr.modules`) pour brancher un paquet pip sans forker, + un `register()`
   pour un module local. Couche `app`.

Règle des deux axes : on conçoit le contrat + registre + découverte d'office ;
on n'implémente que le starter pack au début (cf. ci-dessous). Ajouter un
module = incrémental.

### Socle intégré vs plugins tiers (extensible ≠ vide)

- **Extensible ≠ livré vide.** XerOCR embarque un **socle de modules « maison »**
  enregistrés d'office, qui utilisent **le même `Protocol`** que les modules
  tiers. Seule diffère la livraison : intégré (`xerocr/adapters/`) vs
  installé/déposé.
- **Starter pack** : `precomputed` (0 dép), `tesseract` (binaire requis),
  `openai` + `ollama` (LLM), un segmenteur de référence. Le reste = incrémental
  via plugin.
- **Dépendances lourdes = extras optionnels.** L'adapter est intégré, son SDK
  est un extra (`pip install xerocr[llm]`). Sans l'extra, le module reste listé
  mais signale qu'il faut l'installer (+ clé API) — il ne plante pas.
- **Adapter sain ≠ shim.** Un module enveloppe une lib externe pour la traduire
  vers le `Protocol` (sain, rôle de la couche 5). Interdit : un double contrat
  interne (le wrapping `BaseOCRAdapter`→`BaseModule` de Picarones). Le `Protocol`
  est le contrat unique, implémenté directement.
- **3 contreparties à tenir** : (1) chaque point d'extension est une **API
  publique** (engagement de stabilité → en limiter le nombre) ; (2) le code
  tiers **s'exécute in-process** (sécurité ; cf. mode public) ; (3) un module
  **déclare sa version** (reproductibilité → alimente `RunManifest`).
- **Périmètre STRICT : le seul et unique point d'extension = les briques de
  pipeline** (segmentation, OCR/HTR, VLM, post-correction LLM, construction
  d'ALTO, ordre de lecture, NER… — tout ce qui est une étape `IMAGE/TEXTE/… →
  artefacts`). **Rien d'autre n'est pluggable.** Les métriques, les importeurs
  de corpus, les sections de rapport, les projecteurs, les tests statistiques
  restent **internes (first-party)**, non extensibles par des tiers. On n'ouvre
  **aucune autre prise** — une seule API publique d'extension, point.

### Segmentation / mise en page

Pipeline : `segmentation (IMAGE → LAYOUT régions-seules) → reconnaissance par
région (remplit le LAYOUT) → assemblage (LAYOUT → ALTO_XML)`.

Type structurel unique : `ArtifactType.LAYOUT`, payload `CanonicalLayout` (modèle
neutre ALTO/PAGE). Pas de type `REGIONS` séparé : une sortie de segmentation est
un `CanonicalLayout` à régions sans lignes.

- Couche 1 : `ArtifactType.LAYOUT` + `region_id` optionnel sur `Artifact`. Le type
  `CanonicalLayout` vit en `domain`, matérialisé à la migration couche 2 (backlog).
- Couche 4 : fan-out — reconnaissance une fois par région, collecte des N
  résultats, gestion des échecs partiels, réassemblage par ordre de lecture.
- Couche 3 : métriques par bloc (CER par région + agrégat page). Segmentation et
  structure mesurées sur le même `CanonicalLayout` ; niveau absent → métrique non
  applicable (`None`).
- Routage par type de bloc : moteur différent selon le label de région.

---

## 4. Stratégie de migration

1. **Couches 1-2 (`domain`, `formats`) : approche horizontale, complète, d'abord.**
   Petites, stables, sans dépendance externe, déjà analysées. Les faire à fond
   donne une fondation sûre.
2. **Couches 3-8 : approche par tranches verticales (squelette ambulant).**
   Une fois `domain`+`formats` posées, construire d'abord une tranche fine qui
   traverse toutes les couches pour qu'un cas minimal tourne de bout en bout
   (ex. `xerocr demo` : corpus pré-calculé → 1 CER → HTML basique → CLI).
   **Le squelette n'est pas « petite ambition » : il est fin mais de pleine
   profondeur, et son rôle est de prouver que l'enveloppe dimensionnée tient
   debout avant d'y verser des features.** Puis épaissir feature par feature.
3. **Ordre toujours interne → externe.** Jamais commencer par `interfaces`.

---

## 5. Les 5 garde-fous de discipline (NON NÉGOCIABLES)

Ce sont eux, et non le choix incrémental, qui empêchent le dérapage « dans tous
les sens ». Ils étaient absents de Picarones.

1. **Rupture nette, zéro shim.** Un seul format de sortie (`RunResult`). Jamais
   d'ancien chemin gardé « le temps de migrer ». Aucun helper de conversion
   entre deux représentations.
2. **Budgets par fichier.** Pas de fichier > 400 LOC sans entrée justifiée dans
   `test_file_budgets`. Un fichier ne peut pas enfler en silence.
3. **Pas de consommateur = supprimé.** Tout symbole/fichier sans usage réel en
   CI est retiré. Aucune feature spéculative « au cas où ».
4. **Tests d'architecture dès le jour 1.** layer-deps, no-legacy-imports,
   file-budgets, no-broad-except, no-side-effect-imports, single-version-source.
5. **Une feature = ajoutée entièrement, dans un budget, en élaguant.** On
   n'empile pas ; on intègre proprement.

---

## 6. Décisions déjà actées

- **`BaseModule` (`module_protocol.py`) : contrat unique, construit en couche
  4.** L'extensibilité tierce est une exigence d'enveloppe → on construit **un
  seul `Protocol` de module exécutable**, implémenté directement (pas l'ancien
  double contrat emballé). **Mais il vit en `pipeline` (couche 4)**, pas en
  `domain` : sa méthode `execute()` porte deadline + annulation (`RunControl`,
  couche 4). Donc `module_protocol.py` n'est **pas** recréé en `domain` ; la
  couche 1 ne garde que le déclaratif (`PipelineStep`, `ArtifactType`). Registre
  + découverte entry-points en `app`.
- **Moteur narratif : SUPPRIMÉ entièrement.** `facts.py` non migré ; tout
  `reports/narrative/` abandonné. Le rapport affiche chiffres et tableaux bruts.
- **Purge du legacy résiduel** : `LEGACY_VALUE_ALIASES` (artifacts), shim
  `pipeline_names` + `_accept_legacy_pipeline_names` du `RunManifest`.
- **Renommage racine d'erreurs** : `PicaronesError` → `XerOCRError`.
- **Nettoyage transverse** : aucune annotation de sprint (`S4`, `A14`, `Phase
  7.1`…), aucune référence à `BACKLOG_POST_LIVRAISON.md`.

---

## Critère d'appartenance à la couche 1 (domain) & backlog

Un fichier est couche 1 (`domain`) **seulement** s'il réunit les **3 conditions** :

1. c'est un **type ou contrat pur** (Pydantic / dataclass frozen / Enum / Protocol
   / Error), pas du calcul ;
2. c'est du **vocabulaire transversal**, agnostique des spécificités d'une seule
   couche externe (pas « format ALTO », pas « métrique CER », pas « DTO HTTP ») ;
3. il ne porte **ni contenu chargé** (vs référence) **ni instance d'une couche
   externe**.

⚠️ « N'importe que stdlib + pydantic » **ne suffit pas** : beaucoup d'algorithmes
(métriques, stats, rendu) sont import-propres sans être des types domain.

**Corollaire (inner → outer)** : on **ne crée pas** un type domain avant que son
premier consommateur existe (garde-fou « pas de consommateur = supprimé »), et on
ne fige pas une forme qui dépend d'une couche non encore conçue.

**Backlog domain** — types repérés dans Picarones qui devront atterrir en
`domain`, **à créer quand on migre leur couche propriétaire** (confirmer la forme
à ce moment-là, pas avant) :

| Type | Source Picarones | Déclencheur |
|---|---|---|
| `CanonicalLayout` (+ `Point`/`BBox`/`Geometry`/`Word`/`Line`/`Region`/`LayoutPage`) | neutre ALTO/PAGE (nouveau) | migration couche 2 |
| `ProjectionReport` | `evaluation/projectors/base.py` | migration couche 3 |
| `RunSpec` (+ `StepSpec`) | `app/schemas/run_spec.py` | migration couche 6 (séparer du loader YAML) |
| `ConfidenceToken` (schéma payload `CONFIDENCES`) | `adapters/ocr/confidences.py` | quand les confidences sont consommées (différable) |

**Non-candidats confirmés** (faux positifs analysés) : `RunContext` (→ couche 4,
fait paire avec `RunControl`), `StoredArtifact` (reste en `adapters/storage`,
usage mono-couche), `StepResult`/`PipelineResult` (forme dépend du fan-out →
décidées au plan couche 4), types ALTO/PAGE (format-spécifiques → couche 2),
payloads GT (contenu chargé → couche 3), `MetricsResult` (vocabulaire métrique →
couche 3), DTO web (transport → couche 8).

---

## 7. Conventions de code

- Python, `snake_case` fichiers/fonctions, `PascalCase` classes, `UPPER_SNAKE`
  constantes.
- **Types purs uniquement en `domain/`** : stdlib + `pydantic` + `pydantic_core`.
  Aucun I/O, aucun calcul métier.
- **Erreurs typées** : lever une sous-classe de `XerOCRError`, jamais
  `Exception`/`ValueError` brut quand l'erreur a un sens métier.
- **Jamais `except Exception: pass`.** Toujours
  `logger.warning("[module] dégradé : %s", e)`.
- **Pas de suffixe `_v2`/`_legacy`** ni de préfixe `Picarones*`. Renommages
  atomiques avant merge.
- **`__init__.py` minces** : aucun effet de bord à l'import (pas de
  `register_default_metrics()` implicite — tout enregistrement est explicite,
  idempotent, testable séparément).
- **Modèles Pydantic** `frozen=True, extra="forbid"` pour les types de domaine.
- Pas de placeholder de version dispersé : une source unique
  (`_version_fallback.FALLBACK_VERSION`), vérifiée par test.

---

## 8. À NE PAS reproduire de Picarones

1. Double format de sortie + shim `BenchmarkResult ↔ RunResult` (~1 570 LOC de
   helpers `_benchmark_*`). → Un seul format `RunResult`.
2. Renderers HTML sans interface commune (37 fichiers, 4 signatures). → un
   `Protocol Section` typé unique, 4-5 sections.
3. Data-layer `reports/html/data/` qui ré-agrège `evaluation/`. → consommer
   `RunResult` directement.
4. Workflows CLI pré-câblés (`diagnose`/`economics`/`edition`). → seulement
   `run`/`report`/`compare`/`demo`/`serve`.
5. Sécurité web éclatée en 7 modules `security_*`. → un package `security/`.
6. Noms à suffixe interne dans le code livré (`_v2`, `legacy`).
7. Commentaires de sprint dans le code.
8. 11 profils de normalisation (→ 5), 8+8+8 adapters LLM/VLM (→ minimal),
   20 détecteurs narratifs (→ 0, supprimé).
9. Dossiers de tests vides « par symétrie », `docs/archive`, `CHANGELOG` de
   97 sprints, scripts de refactor morts.

---

## 9. Workflow de migration (conversations)

- **Mémoire durable = fichiers markdown committés.** Chaque couche (ou chaque
  phase verticale) a son plan markdown dans le repo. C'est ce qui permet à une
  conversation fraîche de reprendre sans traîner l'historique.
- **Une conversation par couche** (couches stables 1-2) ou **par phase
  verticale** (couches 3-8). Les grosses couches (`evaluation`, `reports`) se
  sous-découpent par sous-paquet.
- **Ne jamais tout faire dans une seule conversation** : la fenêtre de contexte
  sature, le résumé perd du détail, le taux d'erreur explose.
- Chaque conversation : lit le plan markdown concerné + la source Picarones de
  référence → écrit le code XerOCR + ses tests → vérifie
  (`mypy`/`ruff`/`pytest`) → commit sur la branche.

---

## 10. Tests

- Activer les **tests d'architecture dès le premier commit de code** (ils
  passent même avec peu de code et verrouillent la structure).
- Chaque type/fonction de domaine testé en isolation (validateurs, hash
  déterministe, immutabilité, sérialisation).
- **Golden snapshots** refaits (pas hérités) : `RunResult` canonique + topologies
  de pipeline.
- **Mini-corpus de référence** recopiable de Picarones
  (`tests/fixtures/reference_corpus/`).
- Markers `slow`/`network`/`live` opt-in.
- Cible couverture : 80 % au MVP, 85 % ensuite.

---

## 11. Commandes

À renseigner quand le packaging existe (`pyproject.toml` + extras). Cible :

```bash
pip install -e ".[dev]"      # installation dev
make test                    # pytest
make lint                    # ruff + mypy
xerocr demo --output r.html  # rapport démo sans moteur (squelette)
```

---

## 12. Invariants produit (à préserver coûte que coûte)

- **Déterminisme** : même spec + même corpus + même code → mêmes artefacts
  (hash identique), mêmes métriques, même rapport.
- **Reproductibilité** : `RunManifest` porte code_version + deps + binaires +
  hash des paramètres.
- **Sécurité XML** : tout XML via `safe_parse_xml` (defusedxml, no DTD).
- **Sécurité chemins** : tout chemin utilisateur via `validated_path()` ;
  défense path-traversal (rejet `..`) jusque dans les validateurs de domaine.
- **Anti-hallucination rapport** : aucun LLM ne génère de prose dans le
  rapport ; tous les nombres sont une fonction auditable des données d'entrée.
- **Annulation/timeout coopératifs** via `Deadline` + `RunControl`.
