.PHONY: install lint type test check ci

install:
	pip install -e ".[dev]"

lint:
	ruff check xerocr/ tests/

type:
	python -m mypy -p xerocr

test:
	python -m pytest -q

check: lint type test

# Porte unique avant push : ruff + mypy + suite COMPLÈTE.
# Règle (CLAUDE.md §11) : ne jamais rapporter « vert » sur un sous-ensemble.
ci: check

