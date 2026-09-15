.PHONY: test test-cov lint

PYTHON ?= python
PYTEST ?= $(PYTHON) -m pytest

test:
	$(PYTEST) -q

test-cov:
	$(PYTEST) -q --cov=almasix.permission --cov-report=term-missing --cov-fail-under=98

lint:
	$(PYTHON) -m ruff check src tests
	$(PYTHON) -m ruff format --check src tests
