# Tools

PYTHON ?= python3
PYLINT ?= pylint
PYTEST ?= py.test-3

# Variables

PYTHONPATH ?= .
ARGS ?=

# Rules

.PHONY: all
all:

.PHONY: lint
lint:
	$(PYLINT) ./grapi

.PHONY: test
test:
	PYTHONPATH=${PYTHONPATH} ${PYTEST}

# Dev helpers

.PHONY: start-mfr
start-mfr:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) grapi/mfr/__init__.py $(ARGS)

.PHONY: start-devrunner
start-devrunner:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) scripts/devrunner.py $(ARGS)
