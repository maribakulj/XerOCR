"""``HistoryStore`` — historique **longitudinal** des runs, en SQLite (couche 5).

Persiste, run après run, la **valeur agrégée de chaque métrique** par pipeline et
par vue, pour suivre l'évolution dans le temps (tendance) et **détecter les
régressions** (un moteur dont le CER se dégrade d'un run au suivant).

Le store ne connaît **que des enregistrements primitifs** (``HistoryRecord``) : il
n'importe pas ``RunResult`` (couche 3) — c'est la couche ``app`` qui aplatit un
``RunResult`` en enregistrements (``app/history.py``). Persistance pure, réutilisable
et testable avec de la donnée simple.

Concurrence : **une connexion par opération** (``sqlite3.connect`` est bon marché),
donc aucun partage de connexion entre threads. Ré-enregistrer un même run est
**idempotent** (clé primaire ``(run_id, pipeline, view, metric)``).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS run_metrics (
    run_id       TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    corpus_name  TEXT NOT NULL,
    code_version TEXT NOT NULL,
    pipeline     TEXT NOT NULL,
    view         TEXT NOT NULL,
    metric       TEXT NOT NULL,
    value        REAL NOT NULL,
    PRIMARY KEY (run_id, pipeline, view, metric)
);
CREATE INDEX IF NOT EXISTS idx_run_metrics_lookup
    ON run_metrics (view, metric, pipeline, completed_at);
"""

_COLUMNS = (
    "run_id, completed_at, corpus_name, code_version, pipeline, view, metric, value"
)


@dataclass(frozen=True)
class HistoryRecord:
    """Une valeur de métrique agrégée pour un run (ligne d'historique)."""

    run_id: str
    completed_at: str  # ISO 8601 (UTC) — triable lexicographiquement
    corpus_name: str
    code_version: str
    pipeline: str
    view: str
    metric: str
    value: float


@dataclass(frozen=True)
class Regression:
    """Dégradation d'un pipeline entre ses deux runs les plus récents."""

    pipeline: str
    view: str
    metric: str
    previous_run_id: str
    latest_run_id: str
    previous: float
    latest: float
    delta: float  # latest - previous (signé)


class HistoryStore:
    """Historique longitudinal sur un fichier SQLite."""

    def __init__(self, db_path: str | Path) -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self._path)) as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    def add(self, records: Iterable[HistoryRecord]) -> int:
        """Enregistre des lignes (``INSERT OR REPLACE``) ; renvoie le compte."""
        rows = [
            (
                r.run_id,
                r.completed_at,
                r.corpus_name,
                r.code_version,
                r.pipeline,
                r.view,
                r.metric,
                r.value,
            )
            for r in records
        ]
        if not rows:
            return 0
        with closing(sqlite3.connect(self._path)) as conn:
            conn.executemany(
                f"INSERT OR REPLACE INTO run_metrics ({_COLUMNS}) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
            conn.commit()
        return len(rows)

    def history(
        self, pipeline: str, view: str, metric: str
    ) -> tuple[HistoryRecord, ...]:
        """Suite chronologique (croissante) d'une métrique pour un pipeline/vue."""
        with closing(sqlite3.connect(self._path)) as conn:
            cur = conn.execute(
                f"SELECT {_COLUMNS} FROM run_metrics "
                "WHERE pipeline = ? AND view = ? AND metric = ? "
                "ORDER BY completed_at",
                (pipeline, view, metric),
            )
            return tuple(HistoryRecord(*row) for row in cur.fetchall())

    def regressions(
        self,
        view: str,
        metric: str,
        *,
        threshold: float = 0.0,
        higher_is_better: bool = False,
    ) -> tuple[Regression, ...]:
        """Pipelines dont la métrique s'est dégradée entre les 2 derniers runs.

        ``higher_is_better=False`` (défaut, CER/WER) : régression = la valeur a
        **augmenté** de plus de ``threshold``. ``True`` inverse le sens.
        """
        with closing(sqlite3.connect(self._path)) as conn:
            cur = conn.execute(
                "SELECT pipeline, completed_at, value, run_id FROM run_metrics "
                "WHERE view = ? AND metric = ? ORDER BY pipeline, completed_at",
                (view, metric),
            )
            rows = cur.fetchall()

        by_pipeline: dict[str, list[tuple[str, float, str]]] = {}
        for pipeline, completed_at, value, run_id in rows:
            by_pipeline.setdefault(pipeline, []).append((completed_at, value, run_id))

        out: list[Regression] = []
        for pipeline, series in by_pipeline.items():
            if len(series) < 2:
                continue
            _, prev_value, prev_run = series[-2]
            _, last_value, last_run = series[-1]
            delta = last_value - prev_value
            worse = -delta if higher_is_better else delta
            if worse > threshold:
                out.append(
                    Regression(
                        pipeline=pipeline,
                        view=view,
                        metric=metric,
                        previous_run_id=prev_run,
                        latest_run_id=last_run,
                        previous=prev_value,
                        latest=last_value,
                        delta=delta,
                    )
                )
        return tuple(out)


__all__ = ["HistoryRecord", "HistoryStore", "Regression"]
