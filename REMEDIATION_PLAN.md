# REMEDIATION_PLAN.md — durcissement post-audit (sans bricolage)

> Plan de correction issu de l'**audit impitoyable** de la session T7/S6 (cf.
> `MIGRATION_PLAN.md` journal **D-050**). Principe : chaque item est soit
> **corrigé proprement avec test** + **suite complète verte** avant push, soit
> **accepté explicitement** avec justification (jamais un silence). Tranches
> verticales, une chose à la fois.
>
> **Décisions produit actées** (utilisateur) :
> - **D1** = type domaine dédié pour l'OCR-référence (≠ GT manuelle).
> - **D2** = import HuggingFace **matérialisé**, **convention XerOCR seule** +
>   **streaming** (pas de snapshot local complet).
> - **D3** = vérification distante par **cassettes enregistrées** (rejouables, CI).

## Déjà corrigé (D-050, mergé dans `main`)
- [x] Fuite de jeton sur **redirection cross-hôte** (`_http`) — strip si l'hôte change + test.
- [x] Fuite de jeton via **`next` eScriptorium cross-hôte** — refus hors hôte.
- [x] **Décalage page Gallica** (canvas sauté) — vue lue dans l'URL `/f{n}/` + test qui échoue sur l'ancien code.
- [x] **Déterminisme régressions** — `ORDER BY …, run_id`.
- [x] `mufi_err` chevauchait `diacritic_err` (bloc combinant retiré).
- [x] `_extract_label` pouvait renvoyer non-`str`.
- [x] `materialize` testé en direct ; page `/history` bornée.

## Lots restants (ordre d'exécution)

### Lot 0 — Garde-fou process ✅ (ce commit)
- [x] `make ci` (= `make check` : ruff + mypy + **pytest complet**).
- [x] Règle écrite (`CLAUDE.md §11`) : **jamais rapporter « vert » sur un sous-ensemble** ; `make check` obligatoire avant tout push. *(Cause racine de la CI rouge non vue pendant 11 commits.)*

### Lot A — Sécurité : anti-DNS-rebinding réel (#2) ✅ (D-051)
- [x] Résoudre **une fois** → valider → **connecter à l'IP épinglée**. Implémenté par un `network_backend` `httpcore` custom (`_PinnedBackend`) : l'URL (donc `Host` + **SNI** + vérif. de certificat TLS) reste **inchangée** ; seule la cible TCP est figée sur l'IP validée. Pas d'override SNI-sur-IP fragile → le risque TLS noté ci-dessous **ne se présente pas**. Ré-épinglage par redirection (`_stream_validated`, client par saut).
- [x] Test : `getaddrinfo` mocké (public à la validation, loopback ensuite) → la connexion vise l'IP **validée** (interception de la cible réelle du transport) + une **seule** résolution DNS (`test_connection_pins_validated_ip_not_rebind`). Non-régression SSRF + redirect-auth verte.
- Risque TLS/SNI : **évité** (URL/Host/SNI préservés, seule la cible TCP change). `httpcore` ajouté à la whitelist archi adapters + aux extras (`httpx` le co-installe).

### Lot B — Robustesse transport
- [ ] **B1** `download` en **flux disque** (`.part` au fil de l'eau, cap, `os.replace` atomique, pas de fichier partiel).
- [ ] **B2** média eScriptorium : `Authorization` autorisé **même-hôte** sur le download (règle host de D-050).

### Lot C — Domaine : type « OCR-référence » (D1)
- [ ] `ArtifactType.REFERENCE_TEXT` (couche 1) ; Gallica écrit `GroundTruthRef(REFERENCE_TEXT)`.
- [ ] **Évaluation** : une GT `REFERENCE_TEXT` n'est pas scorée comme vérité manuelle par défaut (vue/étiquette dédiée ou opt-in) ; rapport distinct.
- [ ] Golden-snapshots refaits ; round-trip JSON.

### Lot D — Import HuggingFace (D2 : convention XerOCR + streaming)
- [ ] Doc **convention XerOCR** (schéma : `image`, `ground_truth`, opt. `segmentation`).
- [ ] Adapter via lib `datasets` (**extra `[huggingface]`**, `streaming=True`) → corpus de travail page-par-page (pas de snapshot).
- [ ] Service `app.import_hf_corpus` + endpoint `/api/corpus/import/huggingface` (CSRF, **gate public 403**) ; dataset non conforme → 422 clair.
- [ ] GT d'un dataset XerOCR curé = **vraie GT** (`RAW_TEXT`).

### Lot E — Vérification cassettes (D3) + fixture Gallica réelle
- [ ] Script de capture (réseau ouvert, **hors sandbox**) → fixtures (IIIF/Gallica `texteBrut`/eScriptorium/HF).
- [ ] Transport « replay » déterministe → valide le **parsing réel** + l'hypothèse Gallica `/f{n}/`.
- ⚠️ **Dépendance** : capture impossible dans le sandbox actuel (allowlist) → nécessite un environnement réseau (ou exécution du script par l'utilisateur).

### Lot F — UX / scalabilité
- [ ] **F1** cache TTL des catalogues découverte (fin du fetch par chargement `/library`).
- [ ] **F3** atomicité import : nettoyage du dossier partiel sur échec.
- [ ] **F2** *(optionnel, gros)* import = job de fond (infra runs : annulable, SSE) si gros corpus visés.

### Lot G — Housekeeping
- [ ] Vérifier/narrower les `except Exception` de `jobs.py`.
- [ ] Accepts mineurs **documentés** : HF `results[:limit]` (#9), pk non-int + warning (#14), `errors=replace` OCR (#15), insert non compté `mufi_err` (#17).

## Contraintes honnêtes
- **Lot E** (cassettes) + toute vraie validation distante : **impossible dans ce sandbox** (allowlist réseau).
- **Lot A** : pinning IP réel si SNI propre ; sinon accept documenté (gate public).
