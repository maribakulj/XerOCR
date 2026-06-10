# Écrire un module XerOCR (plugin tiers)

XerOCR a **un seul point d'extension** : une **brique de pipeline** (segmenteur,
OCR/HTR, VLM, post-correcteur LLM, assembleur d'ALTO, ordre de lecture, NER…).
Tout le reste — métriques, importeurs de corpus, sections de rapport, tests
statistiques — reste **interne (first-party)**, non extensible. Une seule prise,
point (cf. `CLAUDE.md` §3).

## Socle et plugins : **même contrat**, seule la livraison diffère

Un moteur du socle (`tesseract`, `kraken`, `pero`, `calamari`, `google_vision`,
`azure_di`…) et un module tiers implémentent **exactement le même** `Module`
Protocol. Il n'y a **aucune discrimination** de contrat. La seule différence :

| | Socle (first-party) | Plugin (tiers) |
|---|---|---|
| Livraison | intégré (`xerocr/adapters/`), enregistré par `register_default_modules` | paquet pip séparé, découvert par entry-points |
| Dépendance lourde | extra optionnel (`xerocr[kraken]`…) | dépendance du plugin |
| Mode public (Space exposé) | exécutable si dans `PUBLIC_ENGINE_KINDS` (socle gratuit) | **désactivé (fail-closed)** — pas de code tiers in-process |

Autrement dit : « tout est déjà module ». Mettre une brique in-tree ou en plugin
est un choix de **packaging**, pas de contrat.

## Le contrat : `Module` Protocol (couche `pipeline`)

```python
from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.pipeline.protocols import ParamValue
from xerocr.pipeline.run_control import RunControl
from xerocr.pipeline.types import RunContext, StepOutput


class MyOCR:
    def __init__(self, *, label: str, model: str) -> None:
        self._label = label
        self._model = model

    @property
    def name(self) -> str:
        return f"my_ocr:{self._label}"      # "<kind>:<label>"

    @property
    def version(self) -> str:
        return "1.0"                        # → RunManifest (reproductibilité)

    @property
    def input_types(self) -> frozenset[ArtifactType]:
        return frozenset({ArtifactType.IMAGE})

    @property
    def output_types(self) -> frozenset[ArtifactType]:
        return frozenset({ArtifactType.RAW_TEXT})

    def execute(
        self,
        inputs: dict[ArtifactType, Artifact],
        params: dict[str, ParamValue],
        context: RunContext,
        control: RunControl,
    ) -> StepOutput:
        control.raise_if_cancelled()
        # … reconnaître `inputs[ArtifactType.IMAGE]`, écrire la sortie dans
        # `context.workspace_uri`, respecter `context.deadline` …
        return StepOutput(artifacts={ArtifactType.RAW_TEXT: ...})
```

Garanties (runner ↔ module) : le runner fournit tous les `input_types`, une
`Deadline` et l'annulation coopérative ; le module renseigne tous ses
`output_types`, n'avale aucune exception, et lève à l'expiration de la deadline.
Enveloppez une lib externe pour la traduire vers ce Protocol — **jamais** un
second contrat interne (la dette que XerOCR abandonne).

## Le builder + l'entry-point

Un **builder** construit l'instance depuis ses kwargs ; le paquet le déclare dans
le groupe `xerocr.modules` :

```python
# mon_paquet/seg.py
from collections.abc import Mapping
from xerocr.pipeline.protocols import Module, ParamValue

def build_my_ocr(kwargs: Mapping[str, ParamValue]) -> Module:
    return MyOCR(label=str(kwargs["label"]), model=str(kwargs["model"]))
```

```toml
# pyproject.toml du plugin
[project.entry-points."xerocr.modules"]
my_ocr = "mon_paquet.seg:build_my_ocr"
```

`pip install mon-paquet` suffit : `discover_plugins` enregistre `my_ocr` dans le
registre runtime **comme le socle**. Le `kind` (`my_ocr`) devient référençable
dans une spec (`adapter_name = "my_ocr:c0"`).

## Trois contreparties (à tenir)

1. **API publique** = engagement de stabilité → on limite les points d'extension à
   un seul (la brique de pipeline).
2. **Exécution in-process** → en mode public la découverte est **désactivée**
   (sécurité d'un serveur exposé).
3. **Version déclarée** → alimente `RunManifest.module_versions` (reproductibilité).

## Quand in-tree, quand plugin ?

- **In-tree** (comme `kraken`/`pero`/`calamari`) : moteur établi qu'on veut
  maintenir dans le socle ; dép lourde en extra ; potentiellement exécutable sur un
  Space **privé**.
- **Plugin** : module expérimental/tiers, ou qu'on ne veut pas dans la surface du
  cœur ; installé à part, **désactivé** sur le Space public.

Les deux passent par le **même** `Module` Protocol.
