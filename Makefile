.PHONY: install lint type test test-fast check ci

install:
	pip install -e ".[dev]"

lint:
	ruff check xerocr/ tests/

type:
	python -m mypy -p xerocr

test:
	python -m pytest -q

# Boucle locale rapide : suite SANS coverage (~3× plus rapide). Le tracing
# `coverage` est l'essentiel du coût de `make test`/`ci`. Ne remplace PAS le
# gate (`make ci` garde coverage + le seuil 85 % — CLAUDE.md §11).
test-fast:
	python -m pytest -q --no-cov

check: lint type test

# Porte unique avant push : ruff + mypy + suite COMPLÈTE.
# Règle (CLAUDE.md §11) : ne jamais rapporter « vert » sur un sous-ensemble.
ci: check

