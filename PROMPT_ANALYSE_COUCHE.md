# Prompt — Session d'ANALYSE d'une couche (XerOCR)

Workflow : voir [`CLAUDE.md`](CLAUDE.md) §9. Une **session d'analyse** produit un
guide de portage **durable** ; elle **ne code rien**. La construction se fait
ensuite par **tranches verticales** dans d'autres sessions.

**Mode d'emploi** : ouvrir une conversation Claude Code **fraîche**, remplacer
`<COUCHE>` (ex. `pipeline`, `adapters`, `app`, `reports`, `interfaces`) et `<N>`
(numéro de couche), coller le bloc ci-dessous.

---

```
Tu démarres une session d'ANALYSE dédiée à la couche `<COUCHE>` de XerOCR
(réécriture propre de Picarones). Ton but : produire un GUIDE DE PORTAGE DURABLE.
Tu n'implémentes AUCUN code XerOCR dans cette session.

== AVANT TOUT (non négociable) ==
1. Lis INTÉGRALEMENT `CLAUDE.md` à la racine (le contrat de travail du projet).
2. Lis les docs déjà committés : tous les `xerocr/**/ANALYSE_COUCHE_*.md` et
   `xerocr/**/MIGRATION_COUCHE_*.md` (décisions déjà actées + contrats des couches
   internes dont tu dépends).
3. Regarde ce qui est déjà mergé dans `xerocr/` (`git log --oneline`, arborescence)
   pour ne RIEN contredire.
Si une de tes conclusions contredit `CLAUDE.md` ou une couche déjà mergée,
SIGNALE-le explicitement et arrête-toi pour clarifier — ne passe jamais outre.

== ANALYSE (source figée Picarones = savoir durable) ==
Source en lecture seule : `../Picarones/picarones/<COUCHE>/`.
- Inventaire exact (fichiers + LOC).
- Pour la breadth, lance PLUSIEURS sous-agents d'exploration EN PARALLÈLE qui
  lisent le code, puis synthétise TOI-MÊME — ne fais pas confiance à un rapport
  d'agent sans recouper les points décisifs dans le code.
- Document par document : rôle réel **vérifié dans le code** (jamais supposé),
  bugs et problèmes, code mort, doublons, dépendances (internes + libs externes),
  couplages, et CONSOMMATEURS RÉELS (grep dans `picarones/`, hors `tests/`).
- Verdict par fichier : GARDER / MODIFIER / CHANGER DE COUCHE / SUPPRIMER +
  justification courte — chaque verdict **marqué « PROVISOIRE — à confirmer au
  build »** (le contact du code corrige souvent l'analyse).

== LIVRABLE : `xerocr/<COUCHE>/ANALYSE_COUCHE_<N>.md` ==
- SCANNABLE : tableaux + verdicts, prose minimale. Il sera lu par de futures
  sessions à budget de contexte limité — ne le gaspille pas.
- Sépare clairement DEUX parties :
  (1) ANALYSE DE LA SOURCE Picarones — durable ;
  (2) IDÉE DE RÉORGANISATION CIBLE XerOCR — périssable, marquée « à confirmer à
      la tranche », conforme à la discipline `CLAUDE.md` : deux axes (enveloppe
      plein-scope vs surface incrémentale), « pas de consommateur = supprimé »,
      budgets < 600 LOC, rupture nette zéro shim, moteur narratif supprimé.
- Liste les RISQUES DE TRANSFERT et les DETTES POTENTIELLES à surveiller, avec,
  quand c'est possible, comment les détecter / les désamorcer.

== INTERDITS ==
- Aucune implémentation de code XerOCR (analyse seulement).
- Aucun plan « construire toute la couche de haut en bas » : la construction se
  fera par TRANCHES VERTICALES, pas en complétant la couche.
- Aucune PR.

== FIN ==
- `git add` du doc, commit (`docs(<COUCHE>): analyse de portage couche <N>`),
  push sur la branche de la session (retry réseau avec backoff 2/4/8/16s si besoin).
- Termine par un résumé des 3 à 5 points les plus importants à transmettre à la
  future session de construction.
```

---

> Note : pour une couche **riche en contrats** (ex. `evaluation`), une session
> séparée pourra ensuite produire le `MIGRATION_COUCHE_<N>.md` (l'**enveloppe** :
> contrats plein-scope + ordre des tranches), en s'appuyant sur l'analyse durable.
> Pour les autres couches, l'analyse suffit ; les contrats minimaux émergent à la
> première tranche qui les traverse.
