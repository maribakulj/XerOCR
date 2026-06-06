"""Résolution du dossier de **données inscriptible** (couche 6).

Distinct du dossier des rapports *bakés* (livrés dans l'image d'un Space, donc
appartenant à root et **non inscriptibles** par l'utilisateur non-root qui sert
l'app). L'historique longitudinal et le puits des rapports de run y vivent —
**jamais** dans le dossier baké, sous peine d'``OperationalError`` / d'échec
d'écriture (cause des *Internal Server Error* sur Hugging Face).

Ordre de résolution : argument explicite › ``XEROCR_DATA_DIR`` › ``/data``
(montage de stockage persistant Hugging Face, s'il est inscriptible) › dossier
temporaire neuf. Le dernier recours est **toujours inscriptible** : on ne
démarre jamais sur un emplacement qui fera planter la première écriture.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

#: Surcharge explicite de l'emplacement de données.
DATA_DIR_ENV = "XEROCR_DATA_DIR"

#: Montage du stockage persistant d'un Space HF (présent si l'option est activée).
_PERSISTENT_MOUNT = Path("/data")


def _is_writable_dir(path: Path) -> bool:
    return path.is_dir() and os.access(path, os.W_OK)


def resolve_data_dir(data_dir: Path | str | None = None) -> Path:
    """Renvoie un dossier de données **inscriptible**, créé au besoin.

    Argument explicite > ``XEROCR_DATA_DIR`` > ``/data`` (si inscriptible) >
    dossier temporaire. Éphémère en dernier recours (la persistance durable est
    obtenue en pointant ``XEROCR_DATA_DIR`` / ``/data`` sur un volume stable).
    """
    if data_dir is not None:
        chosen = Path(data_dir)
    elif env := os.environ.get(DATA_DIR_ENV):
        chosen = Path(env)
    elif _is_writable_dir(_PERSISTENT_MOUNT):
        chosen = _PERSISTENT_MOUNT / "xerocr"
    else:
        chosen = Path(tempfile.mkdtemp(prefix="xerocr-data-"))
    chosen.mkdir(parents=True, exist_ok=True)
    return chosen


__all__ = ["DATA_DIR_ENV", "resolve_data_dir"]
