"""Transport web (couche 8) — sous-paquet servi par la commande ``serve``.

Mince et **sans effet de bord à l'import** : aucun ``app = FastAPI()`` ni routeur
au niveau module (gate ``no_side_effect_imports``). Tout est construit à la
demande par ``create_app()`` (``xerocr.interfaces.web.app``). Les dépendances
``fastapi``/``uvicorn`` sont un **extra** (``pip install 'xerocr[serve]'``) : le
CLI reste installable sans elles.
"""

from __future__ import annotations
