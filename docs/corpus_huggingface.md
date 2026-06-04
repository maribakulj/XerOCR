# Convention XerOCR — datasets HuggingFace

Pour importer un dataset HuggingFace comme corpus **scorable**, le dataset doit
suivre la **convention XerOCR** : des colonnes nommées de façon fixe (XerOCR ne
devine pas un mapping arbitraire — convention unique, pas de configuration).

## Colonnes

| Colonne | Requis | Type | Rôle |
|---|---|---|---|
| `image` | **oui** | image (stockée en octets) | la page à transcrire |
| `ground_truth` | **oui** | `string` | la transcription manuelle = **vraie** vérité-terrain (`RAW_TEXT`) |
| `segmentation` | non | *(réservé)* | mise en page par région — **extension future**, ignorée pour l'instant |

- La colonne `image` doit stocker l'image **encodée en octets** (cas par défaut
  d'un dataset HF utilisant la feature `Image`). L'import lit ces octets
  directement (`Image(decode=False)`) — aucune dépendance de décodage.
- Une ligne dont `ground_truth` est vide donne une page **image-seule** (OCR-able,
  non scorée). Une ligne sans octets d'image est rejetée.

## Comportement de l'import

- **Streaming** (`streaming=True`) : les pages sont lues **une par une**, jamais
  de snapshot local complet. `limit` borne le nombre de pages.
- Un dataset sans les colonnes requises → erreur **422** claire (la conformité
  est validée sur la première ligne).
- La lib `datasets` est un **extra** : `pip install xerocr[huggingface]`. Sans
  elle, l'import signale qu'il faut l'installer (**409**), il ne plante pas.
- En **mode public** (Space exposé), l'import distant est **refusé (403)** comme
  les autres importeurs — il fetch côté serveur.

## Exemple

```python
from datasets import Dataset, Features, Image, Value

Dataset.from_dict(
    {"image": ["p1.png", "p2.png"], "ground_truth": ["Au nom de Dieu…", "…"]},
    features=Features({"image": Image(), "ground_truth": Value("string")}),
).push_to_hub("mon-org/mon-corpus-xerocr")
```
