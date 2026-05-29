# Plan de migration — Couche 1 (`domain/`) : Picarones → XerOCR

> **Statut** : plan validé, prêt à exécuter.
> **Périmètre** : uniquement la couche 1 (`domain/`). Les 7 autres couches feront l'objet de plans dédiés.
> **Source** : `Picarones/picarones/domain/` (15 fichiers, 2 401 LOC).
> **Cible** : `XerOCR/xerocr/domain/` (13 fichiers après décisions : `facts.py`
> et `module_protocol.py` non migrés en `domain`). Le contrat de module
> exécutable n'est **pas perdu** : il est construit en couche 4 (`pipeline`),
> voir D1.

---

## 1. Objectif

La couche `domain` est le **cœur typé** du système : elle ne contient que des
définitions de données (le « vocabulaire » du produit), sans aucune logique
métier, sans I/O, sans dépendance à un moteur externe. Elle n'importe que la
bibliothèque standard Python, `pydantic` et `pydantic_core`.

C'est la couche la plus saine de Picarones (~91 % à recopier tel quel). Ce plan
acte les suppressions décidées et liste, fichier par fichier, ce qui est porté,
nettoyé ou abandonné.

---

## 2. Décisions actées (ce qui change par rapport à Picarones)

| # | Décision | Conséquence concrète |
|---|----------|----------------------|
| **D1** | **`BaseModule` : contrat unique de module, construit en couche 4 (pas en `domain`)** | L'extensibilité tierce est une exigence d'enveloppe → on construit **un seul contrat de module exécutable (`Protocol`)** implémenté directement (≠ le double contrat `BaseOCRAdapter`→`BaseModule` de Picarones). **Mais il vit en `pipeline` (couche 4)**, pas en `domain` : sa méthode `execute()` porte des concerns d'exécution (deadline, annulation via `RunControl`, couche 4) — un `Protocol` en `domain` qui les référencerait violerait le sens des dépendances. Donc `module_protocol.py` n'est **pas** recréé en `domain`. La couche 1 ne garde que le **déclaratif** : `PipelineStep` (qui nomme l'`adapter_name` + `input_types`/`output_types`) et `ArtifactType` suffisent à décrire un module dans une spec. Registre + découverte entry-points = couche `app`. |
| **D2** | **Supprimer entièrement le moteur narratif** | `facts.py` **non migré**. XerOCR n'aura pas de synthèse en prose : le rapport affichera les chiffres et tableaux bruts. Supprime aussi, en aval, toute la couche 7 `reports/narrative/` (hors périmètre de ce plan, mais acté). |
| **D3** | Purger le legacy résiduel des fichiers conservés | Voir §4 : `LEGACY_VALUE_ALIASES`, shim `pipeline_names` du `RunManifest`. |
| **D4** | Renommer la racine d'erreurs | `PicaronesError` → `XerOCRError` (et toute la hiérarchie reste). |
| **D5** | Nettoyer les commentaires historiques | Supprimer toutes les annotations de sprint (`S4`, `A14-S29`, `Phase 7.1`…) et les références au fichier inexistant `BACKLOG_POST_LIVRAISON.md`. |
| **D6** | Corriger un glissement de nom | `Fact.engines_involved` → sans objet (facts supprimé). Mais conserver la règle : préférer `pipelines_involved` partout ailleurs. |
| **D7** | **Ajouter `ArtifactType.REGIONS`** | Nouveau type spatial de première classe (boîtes + labels de blocs) produit par un module de segmentation. Dimensionne le domaine pour le pipeline `segmentation → reconnaissance → assemblage`. |
| **D8** | **Ajouter `region_id` optionnel sur `Artifact`** | Permet de représenter « un artefact texte rattaché à une région ». Socle du fan-out par bloc (modèle b, **retenu**) : métriques par bloc + routage par type de bloc. `None` = artefact au niveau page. |

---

## 3. Inventaire source → cible

15 fichiers Picarones → **13 fichiers XerOCR** (`facts.py` et `module_protocol.py`
non migrés en `domain`). Les seuls ajouts de la couche 1 liés à la segmentation
sont `ArtifactType.REGIONS` et `Artifact.region_id` (dans `artifacts.py`).

| # | Picarones (`domain/`) | → XerOCR (`domain/`) | Décision | Transformation |
|---|------------------------|----------------------|----------|----------------|
| 1 | `__init__.py` | `__init__.py` | **KEEP** | Retirer exports de `facts` et `module_protocol` ; supprimer annotations sprint |
| 2 | `_version_fallback.py` | `_version_fallback.py` | **KEEP** | `FALLBACK_VERSION = "0.1.0"` ; mettre à jour la docstring |
| 3 | `artifacts.py` | `artifacts.py` | **KEEP + purge + étendre** | Supprimer `LEGACY_VALUE_ALIASES` + les 3 alias `TEXT/ALTO/PAGE` (garder `_missing_()`) ; **ajouter `ArtifactType.REGIONS` (D7) et le champ `region_id` (D8)** |
| 4 | `artifact_key.py` | `artifact_key.py` | **KEEP** | Recopier tel quel (purge réfs sprint) |
| 5 | `corpus.py` | `corpus.py` | **KEEP** | Supprimer réf. `BACKLOG_POST_LIVRAISON.md` + note « S10 » |
| 6 | `documents.py` | `documents.py` | **KEEP** | Recopier tel quel (conserver la défense path-traversal) |
| 7 | `provenance.py` | `provenance.py` | **KEEP** | Recopier tel quel (purge réfs sprint) |
| 8 | `projection_spec.py` | `projection.py` *(renommé)* | **KEEP** | Recopier tel quel |
| 9 | `errors.py` | `errors.py` | **KEEP + rename** | `PicaronesError` → `XerOCRError` ; purger note legacy `core` |
| 10 | `pipeline_spec.py` | `pipeline.py` *(renommé)* | **KEEP** | Recopier tel quel (purge réfs sprint) |
| 11 | `evaluation_spec.py` | `evaluation.py` *(renommé)* | **KEEP** | Recopier ; purger réf. backlog + mention `compute_metrics (legacy)` |
| 12 | `module_protocol.py` | — | **DROP de `domain` (D1)** | Non migré en `domain`. Le contrat de module exécutable (`Protocol`) est construit en couche 4 (`pipeline`) — voir D1 |
| 13 | `run_manifest.py` | `run.py` *(renommé)* | **KEEP + purge** | Supprimer `pipeline_names` (computed_field) ET `_accept_legacy_pipeline_names` (~67 LOC de shim) |
| 14 | `facts.py` | — | **DROP (D2)** | Non migré |
| 15 | `deadline.py` | `deadline.py` | **KEEP** | Recopier tel quel (type exemplaire) |

> **Note sur les renommages** : `*_spec.py` → nom court (`projection.py`,
> `pipeline.py`, `evaluation.py`) et `run_manifest.py` → `run.py` suivent la
> convention cible (« une entité = un nom court »). Optionnel : on peut garder
> les noms d'origine si tu préfères minimiser le delta cognitif avec Picarones.

---

## 4. Détail des transformations par fichier

### 4.1 `artifacts.py` — purge des alias legacy
- **Conserver** : `ArtifactType` (10 valeurs canoniques), `compute_content_hash`, la classe `Artifact` (frozen, validators id/hash), `_missing_()` (accepte `"text"`/`"alto"`/`"page"` dans les YAML).
- **Supprimer** : le dict `LEGACY_VALUE_ALIASES` + le bloc de commentaire `expand_legacy_keys` (lignes ~133-150). Unique consommateur = `module_policy.py` (couche 3), lui-même destiné à être réécrit.
- **Supprimer** : les 3 attributs alias `TEXT`/`ALTO`/`PAGE` de l'enum. Migrer les call-sites vers les noms canoniques (`RAW_TEXT`/`ALTO_XML`/`PAGE_XML`). *(Hors couche 1 — à traiter quand on portera les couches consommatrices.)*

### 4.2 `run.py` (ex-`run_manifest.py`) — suppression du shim
- **Conserver** : tous les champs reproductibilité (`run_id`, `corpus_name`, `n_documents`, `pipeline_specs`, `adapter_kwargs`, `view_specs`, `code_version`, `started_at/completed_at`, `dependencies_lock`, `system_binaries_lock`, `metadata`), `duration_seconds`, `utcnow()`.
- **Supprimer** : le `computed_field` `pipeline_names` (lignes ~129-139) et le `model_validator` `_accept_legacy_pipeline_names` (lignes ~141-196). Pur shim de compatibilité JSON, sans consommateur une fois l'ancien `reports/html/render.py` abandonné.

### 4.3 `errors.py` — renommage de la racine
- `PicaronesError` → **`XerOCRError`**. Conserver toutes les sous-classes : `ArtifactValidationError`, `ProjectionError`, `CorpusSpecError`, `AdapterStepError`, `DeadlineExceeded`.
- Conserver intégralement la docstring de `DeadlineExceeded` (elle porte un vrai contrat de comportement pour les adapters).
- Supprimer la note historique sur `picarones.core` (lignes ~26-30).

### 4.4 Fichiers recopiés sans changement fonctionnel
`artifact_key.py`, `documents.py`, `provenance.py`, `projection.py`,
`pipeline.py`, `evaluation.py`, `corpus.py`, `deadline.py`, `_version_fallback.py`.
Seules transformations : retrait des annotations de sprint et des références au
backlog inexistant. **Aucune logique ne change.**

### 4.5 `__init__.py` — agrégateur
- Retirer des imports/`__all__` tout ce qui vient de `facts` (`Fact`, `FactType`, `FactImportance`, `DetectorFn`, `DetectorRegistry`, `detect_all`) **et** de `module_protocol` (`BaseModule`).
- **Exporter** `ArtifactType.REGIONS` (le `region_id` est un champ d'`Artifact`, déjà exporté).
- Adapter les chemins d'import aux fichiers renommés.
- Conserver la note expliquant pourquoi `RunResult` n'est PAS dans `domain` (il agrège des couches externes).

### 4.6 `module_protocol.py` — NON migré en `domain` (contrat déplacé en couche 4)
- Le contrat de module **n'est pas perdu**, mais il **ne vit pas en `domain`** :
  sa méthode `execute()` a besoin de la deadline et de l'annulation
  (`RunControl`, couche 4). Un `Protocol` en couche 1 qui les référencerait
  importerait vers l'extérieur → interdit.
- **Décision** : construire **un seul `Protocol` de module exécutable en couche 4
  (`pipeline`)** — `name`, `version` (reproductibilité), `input_types`,
  `output_types`, `execute(inputs, params, contexte d'exécution) → outputs`.
  Implémenté **directement** par chaque module (≠ double contrat de Picarones).
- **Au niveau couche 1**, rien à faire : `PipelineStep` (déclare `adapter_name`
  + `input_types`/`output_types`) et `ArtifactType` suffisent à **décrire** un
  module dans une spec. Registre + découverte entry-points = couche `app`.
- ⚠️ À traiter dans le **plan de la couche 4**, pas ici.

### 4.7 `artifacts.py` — extensions segmentation (D7/D8)
- **Ajouter `ArtifactType.REGIONS`** : sortie d'un module de segmentation —
  liste de boîtes (bbox) + label de bloc (texte/image/tableau/marge…). Type
  spatial de première classe.
- **Ajouter `region_id: str | None`** sur `Artifact` : identifiant de la région
  d'origine quand l'artefact est rattaché à un bloc (ex. le texte reconnu d'une
  seule région). `None` = artefact au niveau page (cas par défaut).
- Ces deux ajouts **dimensionnent le domaine pour le fan-out par bloc (modèle b,
  retenu)** : métriques par région calculées par la couche 3, fan-out géré par
  l'executor (couche 4). Au niveau couche 1, seuls `REGIONS` + `region_id` sont
  requis ; le reste vit dans les couches consommatrices.

---

## 5. Renommages transverses (à propager dans tout XerOCR)

| Picarones | XerOCR | Portée |
|-----------|--------|--------|
| `PicaronesError` | `XerOCRError` | Toute la base de code |
| `picarones.domain.*` | `xerocr.domain.*` | Tous les imports |
| `engines_involved` | `pipelines_involved` | Convention (le champ disparaît avec `facts`, mais la règle reste) |
| `code_version="1.0.0"` (placeholder de test) | constante de fixture unique, nommée et documentée à un seul endroit | Tests |

---

## 6. Ordre d'exécution

1. **Squelette** : créer `xerocr/domain/` (fait — ce dossier).
2. **Fichiers sans dépendance interne d'abord** (ordre topologique des imports) :
   `errors.py` → `_version_fallback.py` → `artifacts.py` → `provenance.py`
   → `artifact_key.py` → `documents.py` → `corpus.py` → `projection.py`
   → `evaluation.py` → `pipeline.py` → `deadline.py` → `run.py`.
3. **`__init__.py`** en dernier (il agrège tout).
4. **Tests** (voir §7) écrits en parallèle de chaque fichier.
5. **Vérification** : `mypy --strict xerocr/domain/`, `ruff check`, `pytest tests/domain tests/architecture`.

---

## 7. Tests indispensables (couche 1)

### Domain
- Validateurs Pydantic : `doc_id` rejette `..` et chemins absolus ; `PipelineStep.id` unique et alphanumérique ; `PipelineMode` est un `Literal` strict (rejette toute autre valeur).
- Hash déterministe : `ArtifactKey.hash_hex()` stable et reproductible ; `Artifact.content_hash` validé hex 64 chars ; `hash_hex()` retourne `None` si un input manque.
- `Deadline` : monotonic, `remaining_seconds` jamais négatif, sérialisation cross-process (`to_dict`/`from_dict`/pickle), immutabilité.
- `RunManifest` : round-trip JSON byte-stable **sans** le shim `pipeline_names`.
- `XerOCRError` : la hiérarchie attrape bien toutes les sous-classes.

### Architecture (à activer dès maintenant)
- `test_layer_dependencies` : `domain` n'importe que stdlib + `pydantic` + `pydantic_core`.
- `test_no_legacy_imports` : aucun import de `picarones`, aucun symbole `Fact*`/`BaseModule`.
- `test_single_version_source` : `FALLBACK_VERSION` == `pyproject.toml [tool.setuptools_scm]`.
- `test_no_broad_except` : pas de `except Exception: pass`.
- `test_no_side_effect_imports` : les `__init__.py` ne déclenchent aucun effet de bord.

---

## 8. Definition of Done (couche 1)

- [ ] 13 fichiers créés dans `xerocr/domain/` ; `facts.py` et `module_protocol.py` **non** migrés en `domain`.
- [ ] `ArtifactType.REGIONS` et `Artifact.region_id` ajoutés et testés.
- [ ] Contrat de module exécutable **reporté au plan de la couche 4** (pas un livrable de la couche 1).
- [ ] Aucune occurrence de `PicaronesError`, `BaseModule`, `Fact`, `LEGACY_VALUE_ALIASES`, `pipeline_names`, `BACKLOG_POST_LIVRAISON` dans la couche.
- [ ] Aucune annotation de sprint résiduelle.
- [ ] `mypy --strict` vert sur `xerocr/domain/`.
- [ ] `ruff check` vert.
- [ ] Tests domain + architecture verts.
- [ ] `python -c "import xerocr.domain"` fonctionne sans effet de bord.

---

## 9. Risques & points ouverts

- **Renommage des fichiers `*_spec.py`** : choix de confort. Si tu préfères garder
  `pipeline_spec.py` / `evaluation_spec.py` / `projection_spec.py` / `run_manifest.py`
  à l'identique pour faciliter le diff mental avec Picarones, c'est sans impact
  technique. **→ à confirmer.**
- **Suppression des alias `TEXT/ALTO/PAGE`** : touche ~25 call-sites hors couche 1.
  La couche 1 peut être migrée sans attendre ; les call-sites seront corrigés
  lors du portage des couches consommatrices.
- **`RunSpec`** : vit aujourd'hui en couche 6 (`app/schemas/`). L'architecture cible
  pourrait le rapatrier dans `domain/run.py`. **Hors périmètre de ce plan** —
  à trancher au moment de la couche 6.
