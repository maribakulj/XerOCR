"""CLI XerOCR (couche 8) : ``demo``, ``run``, ``compare``, ``serve``.

``argparse`` (stdlib, aucune dépendance — journal D-007). ``demo`` génère un
rapport de démonstration **déterministe** sans moteur réel : un mini-corpus
pré-calculé en mémoire → ``precomputed`` → CER → ``RunResult`` → HTML autonome.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from xerocr.app import (
    dump_run_result,
    load_run_result,
    load_run_spec,
    resolve_code_version,
)
from xerocr.app import run as run_orchestrator
from xerocr.app.modules import (
    ModuleRegistry,
    discover_plugins,
    register_default_modules,
)
from xerocr.domain.errors import XerOCRError
from xerocr.interfaces.demo import demo_run_spec, write_demo_corpus
from xerocr.reports import default_report_renderer, render_comparison


def demo_to_html() -> str:
    """Exécute la démo et renvoie le rapport HTML (déterministe)."""
    registry = ModuleRegistry()
    register_default_modules(registry)
    discover_plugins(registry, enabled=True)  # CLI local : code de confiance
    with TemporaryDirectory() as tmp:
        corpus = write_demo_corpus(Path(tmp))
        result = run_orchestrator(
            demo_run_spec(corpus),
            registry=registry,
            code_version=resolve_code_version(),
        )
    return default_report_renderer().render(result, title="XerOCR — démonstration")


def _run_demo(output: str) -> int:
    path = Path(output)
    path.write_text(demo_to_html(), encoding="utf-8")
    print(f"Rapport de démonstration écrit : {path}")
    return 0


def _run_config(config_path: str, output: str, json_output: str | None) -> int:
    registry = ModuleRegistry()
    register_default_modules(registry)
    discover_plugins(registry, enabled=True)  # CLI local : code de confiance
    spec = load_run_spec(config_path)
    result = run_orchestrator(
        spec, registry=registry, code_version=resolve_code_version()
    )
    Path(output).write_text(
        default_report_renderer().render(
            result, title=f"XerOCR — {spec.corpus.name}"
        ),
        encoding="utf-8",
    )
    if json_output is not None:
        dump_run_result(result, json_output)
    print(f"Rapport écrit : {output}")
    return 0


def _compare_command(path_a: str, path_b: str, output: str) -> int:
    run_a = load_run_result(path_a)
    run_b = load_run_result(path_b)
    Path(output).write_text(render_comparison(run_a, run_b), encoding="utf-8")
    print(f"Comparaison écrite : {output}")
    return 0


def _load_dotenv(path: Path = Path(".env")) -> list[str]:
    """Charge un fichier ``.env`` (``CLE=valeur`` par ligne) dans l'environnement.

    Sans dépendance. **Ne remplace jamais** une variable déjà définie : l'env réel
    prime (un secret HuggingFace l'emporte sur le ``.env`` local). ``#`` et lignes
    vides ignorés. Renvoie les **noms** chargés (jamais les valeurs) pour une trace
    lisible. C'est le moyen d'entrer ses clés en local (``MISTRAL_API_KEY=…``).
    """
    if not path.is_file():
        return []
    loaded: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")
            loaded.append(key)
    return loaded


def _serve_command(host: str, port: int, reports_dir: str | None) -> int:
    # Clés locales depuis ``.env`` (avant tout : la disponibilité des moteurs est
    # capturée au démarrage). Sur HuggingFace, les secrets du Space priment.
    loaded = _load_dotenv()
    if loaded:
        print(f"Clés chargées depuis .env : {', '.join(loaded)}")
    # uvicorn = extra [serve], importé paresseusement : la CLI reste utilisable
    # (demo/run/compare) sans la pile web installée.
    try:
        import uvicorn  # type: ignore[import-not-found]

        from xerocr.interfaces.web.app import REPORTS_DIR_ENV
    except ImportError:
        print(
            "Erreur : serveur non installé (pip install 'xerocr[serve]').",
            file=sys.stderr,
        )
        return 1
    if host not in ("127.0.0.1", "localhost"):
        # 0.0.0.0 expose le service au réseau : sécurité = responsabilité du
        # déploiement (reverse-proxy, mode public). On le signale, sans bloquer.
        print(
            f"Attention : écoute sur {host} (exposé au réseau). "
            "En public, placez un reverse-proxy et activez le mode public.",
            file=sys.stderr,
        )
    if reports_dir is not None:
        os.environ[REPORTS_DIR_ENV] = reports_dir
    print(f"XerOCR sert sur http://{host}:{port} (Ctrl-C pour arrêter).")
    # On passe la FACTORY à uvicorn (factory=True), jamais un app de module :
    # zéro effet de bord à l'import (gate no_side_effect_imports).
    uvicorn.run(
        "xerocr.interfaces.web.app:create_app",
        host=host,
        port=port,
        factory=True,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="xerocr",
        description="Banc d'essai déterministe de pipelines de transcription.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    demo = subparsers.add_parser(
        "demo",
        help="Génère un rapport de démonstration déterministe (sans moteur).",
    )
    demo.add_argument(
        "-o", "--output", default="rapport_demo.html", help="Fichier HTML de sortie."
    )
    run_cmd = subparsers.add_parser(
        "run", help="Exécute un run décrit dans un fichier YAML."
    )
    run_cmd.add_argument("config", help="Fichier YAML décrivant le run.")
    run_cmd.add_argument(
        "-o", "--output", default="rapport.html", help="Fichier HTML de sortie."
    )
    run_cmd.add_argument(
        "--json",
        dest="json_output",
        default=None,
        help="Écrit aussi le RunResult en JSON (pour comparer plus tard).",
    )
    compare_cmd = subparsers.add_parser(
        "compare", help="Compare deux RunResult JSON → rapport de deltas."
    )
    compare_cmd.add_argument("run_a", help="Premier RunResult (JSON).")
    compare_cmd.add_argument("run_b", help="Second RunResult (JSON).")
    compare_cmd.add_argument(
        "-o", "--output", default="comparaison.html", help="Fichier HTML de sortie."
    )
    serve_cmd = subparsers.add_parser(
        "serve", help="Sert la vitrine web des rapports (extra [serve])."
    )
    serve_cmd.add_argument(
        "--host", default="127.0.0.1", help="Adresse d'écoute (défaut : local)."
    )
    serve_cmd.add_argument(
        "--port", type=int, default=8000, help="Port d'écoute (défaut : 8000)."
    )
    serve_cmd.add_argument(
        "--reports-dir",
        default=None,
        help="Dossier des rapports RunResult JSON à servir.",
    )
    args = parser.parse_args(argv)
    # Les erreurs métier (spec invalide, chemin hors zone…) et d'E/S sont
    # rapportées proprement sur stderr + code de sortie 1 — jamais une trace nue.
    try:
        if args.command == "demo":
            return _run_demo(args.output)
        if args.command == "run":
            return _run_config(args.config, args.output, args.json_output)
        if args.command == "compare":
            return _compare_command(args.run_a, args.run_b, args.output)
        if args.command == "serve":
            return _serve_command(args.host, args.port, args.reports_dir)
    except (XerOCRError, OSError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1
    return 1  # pragma: no cover (sous-commande requise)


__all__ = ["demo_to_html", "main"]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
