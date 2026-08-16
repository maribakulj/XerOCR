# `campaigns/tooling/` — les instruments qui ont produit les campagnes

Archivés le 2026-08-16, **pour la provenance et rien d'autre.**

Les README des campagnes voisines disent « pour reproduire :
`python scripts/vision_benchmark.py …` ». Sans ces fichiers, cette phrase
n'aurait plus de référent et les relevés deviendraient illisibles. Ils
sont donc ici.

## Ce qu'ils ne sont pas

**Le banc de cette plateforme.** La décision qui les a fait quitter
`lidenbrock` disait : *retirés, pas déménagés* — porter un instrument dont
on vient de prouver qu'il fausse ses propres résultats serait porter le
défaut avec.

Et le défaut est précis : `vision_benchmark.py` construisait le manifeste
en parsant l'ALTO de **référence**, puis écrasait chaque texte par celui de
l'OCR. La césure était donc détectée sur la transcription humaine et le
texte venait du moteur — un état qu'aucun run réel ne peut atteindre. Les
deux campagnes archivées ici en héritent sur leurs lignes césurées.

Ce qui remplace ces scripts est ce dépôt : un runner, 24 métriques, des
tests de significativité, et une métrique validée contre le scorer HIPE
officiel.

## Ce qu'ils gardent d'utile

Une chose, et elle vaut d'être reprise plutôt que réinventée :
`ocr_corpus.py` et le sidecar qu'il produit permettent de **rejouer une
entrée d'OCR figée** au lieu de relancer un moteur. C'est ce qui a rendu
la campagne d'août comparable à celle de juillet — même entrée, au bit
près. Le tier `precomputed` d'ici fait la même chose ; la parenté est
notée pour qu'on la voie.

**N'y branchez rien.** Si un de ces fichiers redevient utile, il est
réécrit ici, avec les invariants de cette plateforme, et pas importé.
