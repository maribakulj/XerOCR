# PLAN_FIN_MIGRATION.md — Route unique vers `1.0.0` et gel de Picarones

> Plan **prospectif et linéaire**. Cinq étapes, dans l'ordre d'exécution. On fait
> 1, puis 2, puis 3, etc. Rien en parallèle, rien « au cas où », rien laissé pour
> après. Quand la 1.0 sort, **tout le périmètre gardé est dedans** et Picarones
> peut être gelé sans aucune perte.
>
> **Autorité de statut = roll-up de [`MIGRATION_PLAN.md`](MIGRATION_PLAN.md).** Ce
> fichier ne déclare aucun « fait » : toutes les étapes ci-dessous sont
> **planifiées**. Chaque livraison réconcilie le roll-up dans le même commit.

---

## Où on en est (juin 2026)

XerOCR est déjà très avancé. **Déjà livré** : tout le moteur déterministe
(domain → formats → evaluation → pipeline), le Space web (coquille, lanceur
SSE, persistance, sécurité publique, importeurs IIIF/Gallica/eScriptorium/
HuggingFace/HTR-United, historique SQLite, page segmentation), les moteurs
Tesseract / Kraken / Mistral OCR / OpenAI / Anthropic / Mistral-VLM / Ollama, le
mode VLM zero-shot, la segmentation (CanonicalLayout + fan-out + PP-DocLayout),
et les métriques CER/WER/MER, diacritiques, MUFI, confusion, taxonomie,
diagnostics, **économie mesurée** (jetons réels + temps réel, pas d'estimation),
calibration, statistiques (Nemenyi + bootstrap), synthèse factuelle.

**Ce qui manque pour la 1.0**, et que les cinq étapes ci-dessous couvrent
**entièrement** :

1. Le Space public **n'exécute aucun moteur** (vitrine lecture seule) → le
   visiteur ne peut pas faire un vrai OCR gratuitement. **Manque n°1.**
2. **Parité moteurs** Google / Azure / Pero / Calamari.
3. **Parité d'interface** (rapport interactif, galerie, champs de formulaire).
4. Les **métriques restantes** de Picarones jugées utiles (voir §« Verdict
   métrique » plus bas).
5. La **release 1.0** et le **gel** de Picarones.

---

## Décisions déjà actées

| Décision | Choix |
|---|---|
| **Abandons définitifs** | 8 familles jetées (liste §« Abandons »), validées |
| **NER** | extra optionnel `[ner]`, jamais de silence si absent |
| **Économie** | coûts mesurés réels (déjà l'état du code) — pas de CO₂ |
| **Parité moteurs** | Google + Azure **first-party** (extras `[google]`/`[azure]`) ; Pero + Calamari **first-party in-tree** (comme Kraken — décision révisée D-078 ; le seam plugin reste pour les vrais tiers) |
| **Toutes les métriques gardées** | **obligatoires avant 1.0** (le gel ferme la fenêtre de portage — rien en backlog) |
| **Fin** | release `1.0.0` puis gel immédiat de Picarones |

**Méthode de fidélité** : Picarones n'est **jamais** l'oracle. Toute valeur
attendue d'un test vient d'une référence externe (jiwer, formule publiée,
q-table, cassette HTTP réelle) ou d'un cas calculé à la main. `make ci` complet
avant chaque push.

---

# LES 5 ÉTAPES, DANS L'ORDRE

## Étape 1 — Le Space exécute un vrai OCR gratuit

**C'est le manque n°1 et le point de départ.** Aujourd'hui le Space est une
vitrine qui ne fait tourner aucun moteur. Cible : un visiteur uploade un corpus,
lance Tesseract, reçoit un vrai rapport CER — **sans clé, sans installation**.

| | |
|---|---|
| **Fichiers touchés** | `deploy/Dockerfile.engine` (**nouveau** — image qui contient un moteur, ≠ image vitrine actuelle) : `apt-get install tesseract-ocr tesseract-ocr-fra tesseract-ocr-lat tesseract-ocr-eng`, `pip install .[serve,tesseract]`, `ENV TESSDATA_PREFIX=…`, **`ENV OMP_THREAD_LIMIT=1`**, **smoke-test au build** (`tesseract --version` + `--list-langs | grep -qx fra` + OCR d'une image générée), `USER` non-root · `deploy/requirements.txt` (+`pytesseract`) · `.github/workflows/deploy-space.yml` (build image moteur + **smoke OCR réel** post-déploiement) · `xerocr/interfaces/web/app.py` + `security/` (mode public : exécute **uniquement** le socle first-party gratuit ; plugins et cloud restent gated) · `xerocr/app/engines.py` (Tesseract disponible sur le Space) |
| **Risques** | Cold-start free-tier 2 vCPU → `OMP_THREAD_LIMIT=1` **obligatoire** (sans lui, deadlock OpenMP — incident documenté côté Picarones). Abus public → rate-limit, caps upload, sémaphore jobs, timeout coopératif (déjà en place). Déterminisme → version du binaire Tesseract épinglée et tracée dans `RunManifest`. |
| **Décision incluse (segmenteur)** | Une fois l'image Tesseract déployée, **mesurer le cold-start**, puis trancher pour PP-DocLayout sur le Space : (a) le baker si le free-tier tient, (b) rester en dégradé gracieux (« segmenteur indisponible », il tourne en local), ou (c) monter de tier (budget — ta décision). Aucune des trois ne bloque la 1.0 : le dégradé gracieux est déjà livré. |
| **Fait quand** | Le build échoue si Tesseract/`fra` manque ou si l'OCR dépasse le timeout. Un visiteur fait un vrai run Tesseract sur le Space public sans clé. En mode public, les plugins et le cloud sont gated. `make ci` vert, `/health` < 50 ms. |

---

## Étape 2 — Parité moteurs

Compléter les moteurs côté utilisateur, selon l'arbitrage acté. **Un seul contrat
`Protocol`**, chaque moteur extra-gated, fail-closed sans clé (listé mais
indisponible, jamais de crash). C'est la couche adapters dans son rôle légitime —
**pas** le double contrat qui a plombé Picarones.

| Sous-étape | Contenu | Fichiers touchés |
|---|---|---|
| **2a — Google Vision** | adapter cloud first-party | `xerocr/adapters/ocr/google_vision.py` (**nouveau**), extra `[google]` dans `pyproject.toml`, entrée `xerocr/app/engines.py`, `tests/adapters/ocr/test_google_vision.py` (cassette + valeurs main) |
| **2b — Azure Document Intelligence** | adapter cloud first-party | `xerocr/adapters/ocr/azure_di.py` (**nouveau**), extra `[azure]`, entrée factory, `tests/adapters/ocr/test_azure_di.py` |
| **2c — Pero + Calamari** | **first-party in-tree** (révisé D-078, comme Kraken) | `xerocr/adapters/ocr/{pero,calamari}.py` (**nouveaux**), extras `[pero]`/`[calamari]`, builders + sondes `xerocr/app/engines.py`, `_OCR_ENGINES`, tests mockés ; `docs/PLUGINS.md` documente le seam entry-points `xerocr.modules` pour les **vrais** tiers (déjà prouvé D-034) |
| **2d — Vérifs** | zero-shot déjà livré → test bout-en-bout + doc ; tous les adapters cloud remontent bien `tokens_in/out` (alimente l'économie) | `tests/pipeline/` (spec zero_shot 1 étage IMAGE→texte), `tests/adapters/llm/` (jetons non-`None` sur cassette) |
| **2e — Prompts curés par période** ✅ (D-080) | porter les **16 prompts** Picarones (correction + zero-shot) calibrés par type : médiéval FR/EN, imprimé ancien, presse XIXe FR/EN/DE/européenne. **Donnée curée**, pas de la surface exécutable (comme les profils de normalisation) + **prompt libre dans l'UI** (demande utilisateur — textarea déjà câblé) | `xerocr/prompts/*.txt` + loader (`available_prompts`/`load_prompt`), `Competitor.prompt_name` + résolution `app/run_planning` (mutuellement exclusif avec le prompt libre prioritaire), `<select>` curé au formulaire web + `benchmark.js`, `package-data`, `tests/` (chargement + sélection + résolution) |

| | |
|---|---|
| **Risques** | Croissance de surface → mitigée : un `Protocol`, un test par moteur, extra-gated, fail-closed. Ne **jamais** réintroduire de double contrat interne. Prompts = données versionnées (déterminisme : fichier tracé dans `RunManifest`). |
| **Fait quand** | Google/Azure listés ; avec clé → OCR réel sur cassette ; sans clé → indisponible propre. Pero/Calamari listés in-tree (extras), indisponibles sans leur lib, non déployés au Space. Zero-shot testé. Les 16 prompts sélectionnables **+ prompt libre éditable dans l'UI** (D-080). `make ci` vert. **→ Étape 2 COMPLÈTE (2a–2e).** |

---

## Étape 3 — Parité de l'interface et du rapport

Le web et le rapport portent déjà beaucoup (benchmark, SSE `Last-Event-ID`,
library, history, segmentation, CSRF, rate-limit, i18n FR/EN). Cette étape comble
**le delta** avec Picarones. Tout reste **déterministe, sans LLM** (invariant
anti-hallucination) ; le JS client est en lecture seule, zéro appel réseau.

| Sous-étape | Contenu | Fichiers touchés |
|---|---|---|
| **3a — Rapport interactif** | **compare 2 runs client-side ✅ (D-081)** (`FileReader`+`JSON.parse`, plafond 50 Mo, bandeau sticky, CSP `/reports/` par hash) · **badges moteur A→E ✅ (D-082)** · **deeplinks + sommaire + ARIA ✅ (D-083)** · **navigation clavier + palette daltonien ✅ (D-084)** ; *reste hors-3a* : **formatage des nombres FR/EN** = en réalité une **i18n complète du rapport** (texte FR uniquement aujourd'hui) → à planifier à part (cf. 3e), pas une sous-tranche 3a | `xerocr/reports/` (`compare.js`+`report.js`/`embedded.py` + `engine_badges.py` + `renderer.py`) ; la voie server-side `reports/compare.py` reste pour `xerocr compare` |
| **3b — Galerie & drill-in** ✅ | **drill-in diff caractère surligné GT↔hypothèse ✅ (D-085)** · **galerie de documents synthétique ✅ (D-086)** (cartes : aperçu CSS sur la charte + CER par moteur/badges A→E, comme le défaut Picarones — zéro image, autonome) ; **fac-similés réels = opt-in séparé** (canal images base64, décision ultérieure) | `xerocr/reports/text_diff.py` + `sections/gallery.py` + section `diagnostics` |
| **3c — Champs de formulaire** | parité CLI/web : **champ `model` des moteurs OCR ✅ (D-087)** · **`/api/models/{provider}` + suggestions vision ✅ (D-088)** · **preview de normalisation (config YAML custom sans persistance) ✅ (D-089)** · **`char_exclude` ✅ (D-090)** ; *reste* : config save/load JSON ; sélecteur profil métrique ; toggle expose-ALTO | `xerocr/interfaces/web/routers/` + `app/{models,normalization_preview,run_planning}.py` + templates ; la construction de spec reste en `app/run_planning` (garde-fou `interfaces` mince) |
| **3d — Observabilité & a11y** | **`/metrics` Prometheus opt-in ✅ (D-091)** ; *reste* : sélecteur de langue ; tooltips/ARIA ; feedback dropzone ; spinner/progress (vérifier l'existant) | `xerocr/interfaces/web/metrics.py` + `create_app` ; templates |
| **3e — Glossaire FR/EN** | porter le glossaire pédagogique du rapport (définitions CER/WER/ECE/… pour le lecteur non-expert) | `xerocr/reports/glossary/{fr,en}.yaml` (**nouveau**) + intégration dans le rapport (tooltips/section), `package-data`, `tests/` |

| | |
|---|---|
| **Risques** | Garder `interfaces` mince. `/metrics` strictement opt-in. Validation chemins/SSRF maintenue. Golden du rapport reste octet-stable. Glossaire = données i18n (pas de prose LLM). |
| **Fait quand** | Compare hors-ligne, galerie lazy, drill-in diff, deeplinks clavier, nombres localisés, config round-trip, preview normalisation, `/metrics` opt-in, glossaire FR/EN affiché — tous testés. `make ci` vert. |

---

## Étape 4 — Toutes les métriques restantes (l'avant-dernière, comme demandé)

On ajoute **en bloc final** les familles de métriques jugées utiles et encore
absentes de XerOCR. **Aucune n'est optionnelle** : le gel de Picarones ferme la
fenêtre de portage, donc tout ce qu'on garde doit être ici. Chaque famille est
livrée **entièrement** : la métrique + son payload dans `RunResult` + **sa
section de rapport** (le consommateur réel) + ses tests à valeurs calculées main.
Les familles marquées 🔶 sont **réparées** au portage, pas copiées avec leurs
défauts.

| Sous-étape | Familles | Fichiers principaux | Note |
|---|---|---|---|
| **4a — Données structurées & lisibilité** | numerical_sequences (dates/foliation/devises/romains/régnal) ; readability (Flesch delta, révèle la sur-normalisation LLM) | `evaluation/metrics/numerical_sequences.py`, `…/readability.py`, section `reports/sections/structured_data.py` | ✅ copie fidèle ; Flesch borné au **delta relatif**, coefficients FR/EN explicites |
| **4b — Philologie étendue** | abbreviations (scores diplomatique/modernisant) ; early_modern + roman + modern_archives **unifiés** | `evaluation/metrics/abbreviations.py`, `…/early_modern.py` (un seul détecteur roman), étend la section philologie | 🔶 dé-fragmenté : roman compté **une seule fois** (Picarones la comptait deux fois) |
| **4c — Fidélité textuelle** | rare_tokens + lexical_modernization + over_normalization + equivalence_profile **unifiés en une famille** | `evaluation/metrics/textual_fidelity.py`, section `reports/sections/textual_fidelity.py` | 🔶 câblage homogène (Picarones : fragmenté) ; seuils explicites ; pas de silence |
| **4d — Robustesse & qualité image** | robustness (dégradations PIL réelles + **re-OCR**) ; image_quality (netteté/bruit/contraste mesurés) | `evaluation/robustness.py`, `evaluation/metrics/image_quality.py`, section `reports/sections/robustness.py` | ✅/🔶 ; `image_predictive` **reste abandonné** ; re-OCR borné + opt-in ; seed PIL fixe |
| **4e — Inter-moteurs & lignes** | inter_engine (divergence Jensen-Shannon + oracle gap) ; error_absorption (gain net OCR→LLM) ; line_metrics (percentiles/Gini) ; **change-point** longitudinal raffiné | `evaluation/metrics/{inter_engine,error_absorption,line_metrics}.py`, raffinement du longitudinal, sections crosses/lignes | 🔶 alignement ligne-à-ligne fiabilisé (Picarones : split `\n` fragile) ; oracle gap = borne documentée ; vrai détecteur de rupture |
| **4f — NER** | F1 par catégorie, entités manquées/hallucinées, appariement IoU 0.5 | `adapters/ner/spacy_extractor.py` (lazy, fail-closed), `evaluation/metrics/ner.py`, section `reports/sections/ner.py`, loader `.entities.json`, extra `[ner]` | recâblée **anti-silence** : GT entités + extra absent → message « installer `xerocr[ner]` », jamais `[]` muet |

| | |
|---|---|
| **Risques** | Ne pas réimporter les défauts 🔶 (fragmentation, silences, alignements naïfs). spaCy strictement en extra. Déterminisme : versions de modèle dans `RunManifest`, seeds fixes. |
| **Fait quand** | Chaque famille a sa section + ses tests à valeurs-main/référence externe ; câblée dans un profil ; **plus aucune famille gardée hors XerOCR**. `make ci` vert, couverture ≥ 85 %. |

---

## Étape 5 — Release `1.0.0` puis gel de Picarones

| Sous-étape | Contenu |
|---|---|
| **5a — Release 1.0.0** | Vérifier la checklist ci-dessous · tag `v1.0.0` · `README` (positionnement 1.0, matrice moteurs/extras, mode Space) · `CHANGELOG` minimal · `pricing.json` daté · roll-up `MIGRATION_PLAN.md` réconcilié |
| **5b — Gel de Picarones** | Bannière `README` Picarones → « projet figé, successeur XerOCR » · dépôt GitHub archivé en lecture seule · note de dépréciation sur le Space HF Picarones (lien vers le Space XerOCR) · plus aucun commit Picarones |

### Checklist « 1.0 prête »

- [ ] **Étape 1** : le Space public exécute Tesseract gratuitement (build fail-fast, OMP borné, `fra` présent) ; décision segmenteur prise.
- [ ] **Étape 2** : Google + Azure first-party, Pero + Calamari first-party in-tree (D-078), zero-shot vérifié, jetons remontés par tous les adapters cloud, **16 prompts curés portés**.
- [ ] **Étape 3** : compare client-side, galerie lazy, drill-in diff, champs de formulaire complets, observabilité/a11y, **glossaire FR/EN porté**.
- [ ] **Étape 4** : **toutes** les familles métriques gardées portées (4a→4f), chacune avec section + tests valeurs-main. Plus aucune famille gardée hors XerOCR.
- [ ] `make ci` vert (3 OS × Python 3.11/3.12), couverture ≥ 85 %, tous les garde-fous d'archi verts.
- [ ] `README`/`CHANGELOG`/`pricing.json` à jour, roll-up réconcilié.
- [ ] Gel de Picarones exécuté (5b).

---

# RÉFÉRENCES

## Abandons définitifs (8) — validés, irréversibles

Ce qui était dans Picarones et **ne sera pas porté** (jugé sans valeur même
réparé → le gel n'en perd rien) :

| # | Famille | Ce que ça faisait | Pourquoi on l'abandonne |
|---|---|---|---|
| 1 | Estimation CO₂ | g CO₂/1000 pages | kWh inventé × intensité conventionnelle ; aucun chiffre mesuré → viole l'anti-hallucination |
| 2 | `image_predictive` | « prédire » le CER depuis la qualité image | stub sans implémentation ; une vraie régression exigerait un entraînement par moteur. La **mesure** de qualité, elle, est gardée (4d) |
| 3 | Calibration au-delà de l'existant | ECE/MCE supplémentaires | XerOCR a déjà `ConfidenceToken` + ECE/MCE ; un seul moteur fournit des confiances → rien à étendre |
| 4 | Registre `levers` (561 LOC) | « leviers d'amélioration » | 561 LOC, dépendances **silencieuses** (pattern narratif déjà supprimé). Les 2-3 observations saines sont repliées dans `synthesis` |
| 5 | taxonomy intra_doc / cooccurrence / comparison | 3 re-projections de la taxonomy | aucune info nouvelle, peu testées, 3 renderers à maintenir. La taxonomy cœur est gardée |
| 6 | `reliability` (Cohen κ / Krippendorff α) | accord inter-annotateurs | plafonné à 2 annotateurs, jamais branché ; outillage de campagne d'annotation, pas de benchmark |
| 7 | `module_policy` | audit de manifeste tiers | zéro module tiers ; les entry-points `xerocr.modules` font déjà mieux |
| 8 | WIL | variante d'erreur mot | quasi-monotone du WER : zéro décision différente, une colonne de plus |

## Verdict métrique-par-métrique (sur pièces)

Synthèse des deux audits de qualité d'exécution. ✅ utile · 🔶 réparable
(réparée au portage) · 🟡 gadget (abandonnée).

| Famille | Verdict | Sur pièces | Destination |
|---|---|---|---|
| CER / WER / MER | ✅ | parité jiwer | livré |
| diacritiques, MUFI, del/ins | ✅ | NFD align, PUA | livré |
| confusion + char_scores | ✅ | Levenshtein minimal (fix F4) | livré |
| taxonomy cœur | ✅ | classes à sens analytique | livré |
| searchability | ✅ | Levenshtein≤2 (Elastic), 21 tests | livré |
| hallucination | 🔶 | trigrammes ; faux positifs diacritiques/multilingue | livré, à durcir |
| economics | ✅ | jetons + temps mesurés | livré (CO₂ exclu) |
| calibration | ✅ | Guo et al. | livré |
| longitudinal | 🔶 | OLS OK ; « CUSUM » = max-diff naïf | livré ; change-point raffiné en 4e |
| numerical_sequences | ✅ | regex conservatrices, recto/verso | **étape 4a** |
| readability (Flesch) | ✅ | formules publiées | **4a** |
| abbreviations | ✅ | 2 scores, pas de GT spéciale | **4b** |
| early_modern + roman + archives | 🔶 | fragmenté, roman doublée | **4b** (unifié) |
| rare_tokens + lexical + over_norm + equivalence | 🔶 | câblage fragmenté | **4c** (unifié) |
| robustness | ✅ | vraies dégradations PIL + re-OCR | **4d** |
| image_quality | 🔶 | mesure OK, constantes crues | **4d** |
| inter_engine | ✅ | Jensen-Shannon + oracle gap | **4e** |
| error_absorption | ✅ | multiset correct | **4e** |
| line_metrics | ✅ | percentiles/Gini ; alignement à fiabiliser | **4e** |
| NER | ✅ | IoU solide, mais découplée chez Picarones | **4f** (recâblée) |
| taxonomy dérivées, CO₂, image_predictive, calibration+, levers, reliability, module_policy, WIL | 🟡 | voir Abandons | **abandonnées** |

## Garde-fous anti-« syndrome Picarones » appliqués à ce plan

- **Un seul plan, linéaire** — plus de double axe T#/S#, plus de phases croisées.
- **Zéro shim** : un seul format `RunResult`, aucun pont vers Picarones.
- **Budgets fichier** : chaque nouveau fichier sous 600 LOC ou entrée justifiée.
- **Pas de spéculatif** : chaque métrique de l'étape 4 a un consommateur (sa
  section). Les 🔶 sont réparées, jamais empilées telles quelles. Les 8 abandons
  restent dehors.
- **Anti-silence** : NER et coûts affichent un message explicite si une
  dépendance/un tarif manque, jamais `[]`/`0` muet.
- **Anti-hallucination** : aucun LLM dans le rapport ; tout nombre est une
  fonction auditable des données d'entrée.
- **`make ci` complet avant chaque push.**
