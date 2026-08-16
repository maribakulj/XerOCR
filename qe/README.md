# `qe/` — le scorer d'estimation de qualité, en dépôt d'attente

Arrivé de [`lidenbrock`](https://github.com/maribakulj/lidenbrock) le
2026-08-16. **Il n'est pas encore branché sur cette plateforme** : ce
dossier est un dépôt, pas une intégration, et il le dit pour qu'on ne le
prenne pas pour l'un ou l'autre.

## Ce que le scorer fait

Il répond à la question qui précède l'appel au modèle : **cette ligne
source porte-t-elle encore une erreur d'OCR, ou est-elle déjà propre ?**
Un score haut envoie la ligne au correcteur ; un score bas permet de la
sauter sans dépenser un appel.

Le signal est la **pseudo-perplexité masquée** d'un modèle de langue
pré-entraîné (Salazar et al., 2020) : un token que le modèle trouve
improbable est une rupture d'OCR probable. **Zéro-shot** — aucun
entraînement de QE ; le modèle informe, l'application décide.

Une propriété qui a demandé du travail et qu'il ne faut pas perdre :
**l'orthographe d'époque n'est jamais un signal d'erreur.** Le scorer lit
une copie dé-glyphée (`ſ→s`, ligatures → ASCII), de sorte que la
perplexité mesure la langue et non la typographie. Le document, lui,
n'est jamais modifié.

## Pourquoi il est ici plutôt que là-bas

La question qu'il pose est **économique** : est-ce que ça vaut le coup
d'appeler le modèle sur cette ligne ? Cette plateforme porte déjà une
section de rapport « économie » — coût, débit, front de Pareto, coût
marginal — et c'est là que la réponse se vérifie.

Et il y était intenable : il exige `onnxruntime` et un **bundle ONNX de
545 Mo** qu'aucune CI ne peut raisonnablement tirer. Sa suite se sautait
donc partout, et son module était exclu de la porte de couverture. Une
bibliothèque qui se prépare à être publiée ne peut pas embarquer un extra
que rien n'exécute.

`lidenbrock` garde le **protocole** `QEScorer` : le point d'injection reste
public, l'implémentation part.

## Ce qu'il faut savoir avant de s'en servir

- **Le modèle est un paramètre, pas une constante.** Le scorer charge un
  bundle auto-descriptif (`model.onnx` + `tokenizer.json` +
  `qe_model.json`) et lit sa calibration dedans.
- **Le réducteur de ligne dépend du registre**, et c'est mesuré : `max`
  pour l'imprimé des 16ᵉ-18ᵉ siècles, `mean` pour la presse du 19ᵉ — avec
  `max`, quelques noms propres font pointer la ligne entière et fabriquent
  des faux positifs.
- **La calibration presse-19e est PROVISOIRE** : elle a été ajustée sur un
  pastiche scripté, pas sur du Gallica réel. À refaire avant d'en tirer
  quoi que ce soit.
- **Aucun canal ne distribue les bundles.** Ils vivaient dans un cache
  local. C'est le premier obstacle à lever si ce scorer doit servir à
  quelqu'un d'autre.

`qe-scorer.md` porte le détail, y compris les mesures par période et par
modèle.

## Ce que « brancher » voudrait dire ici

Le point d'extension de cette plateforme est la **brique de pipeline**, et
un scorer n'en est pas une : il ne transforme pas un artefact, il en juge
un. L'intégrer demande donc un arbitrage — pas un port. À ne pas faire
sans l'avoir tranché.
