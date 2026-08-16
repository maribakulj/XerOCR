# `campaigns/` — les runs mesurés, avec leurs relevés

Archives de campagnes menées sur `lidenbrock` avant que cette plateforme
reprenne le rôle de banc. Elles arrivent avec le corpus qu'elles mesuraient,
le 2026-08-16.

Elles sont ici pour **ce qu'elles ont trouvé**, pas pour leurs chiffres.

## `2026-07-25-bnl-mistral/`

Première mesure réelle : corpus BnL, `mistral-medium`, chaîne vision. Deux
runs, une décimale citée. C'est cette campagne qui a fait écrire la règle
qui gouverne les suivantes : **jamais une décimale isolée.**

## `2026-08-14-bnl-mistral-m2/`

Cinq runs, pour publier une fourchette au lieu d'un nombre. Et la plus utile
des deux, parce qu'elle **invalide ses propres chiffres** :

- fourchette mesurée 0,0338 – 0,0357, écart 5,6 % ;
- puis la campagne découvre que le banc **appariait les césures sur la
  transcription humaine et non sur le texte donné au moteur**, fabriquant un
  état qu'aucun run réel ne peut atteindre ;
- le correctif est arrivé **après** les cinq runs. La fourchette publiée
  hérite donc du défaut qu'elle a trouvé, et le contrefactuel
  (0,0243 – 0,0263) est un re-calcul, pas une mesure.

Deux conclusions valent d'être reprises plutôt que redécouvertes.

**Aucune des deux campagnes n'est fiable sur les lignes césurées.** Le
défaut d'appariement les traverse toutes les deux.

**Et l'item `M4` reposait sur une lecture inversée.** Il disait « récupérer
les 16,5 % de CER dus à deux normalisations systématiques ». Compté contre
l'entrée plutôt que contre la référence : le signe de coupure `⸗`
**n'atteint jamais le modèle** (0 occurrence dans l'OCR d'entrée, 36 dans la
référence), et l'apostrophe typographique est **détruite par l'OCR puis
réparée par le modèle** — 50 lignes améliorées, 0 dégradée. La perte
récupérable, s'il en reste, est en amont dans l'OCR.

## Ce qu'elles impliquent ici

Une campagne rejouée sur ce banc devra fournir ce qu'aucune des deux n'avait :
des **runs répétés** avec leur dispersion. Ce dépôt n'a aujourd'hui aucun
mécanisme pour ça — toute la dispersion qu'il affiche est inter-documents,
jamais inter-runs.
