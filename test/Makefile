DOCKERCOMPOSE ?= docker-compose

BUILD_TAG ?= $(shell date +%s)

export COMPOSE_PROJECT_NAME=grapi-test-$(BUILD_TAG)

# CI

.PHONY: test-backend-kopano-ci-run
test-backend-kopano-ci-run:
	$(DOCKERCOMPOSE) up -d
	$(DOCKERCOMPOSE) run --rm kopano_grapi_test /workspace/test/starttest.sh

.PHONY: test-backend-kopano-ci-clean
test-backend-kopano-ci-clean:
	$(DOCKERCOMPOSE) down -v || true
