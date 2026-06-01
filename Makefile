.PHONY: install lint type test check

install:
	pip install -e ".[dev]"

lint:
	ruff check xerocr/ tests/

type:
	python -m mypy -p xerocr

test:
	python -m pytest -q

check: lint type test
