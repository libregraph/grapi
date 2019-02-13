# Tools

PYTHON ?= python3
PYLINT ?= pylint

# Variables

PYTHONPATH ?= .

# Rules

.PHONY: all
all:

.PHONY: lint
lint:
	$(PYLINT) ./grapi

# Dev helpers

.PHONY: start-mfr
start-mfr:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) grapi/mfr/__init__.py

.PHONY: start-devrunner
start-devrunner:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) scripts/devrunner.py
