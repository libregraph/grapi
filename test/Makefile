DOCKERCOMPOSE ?= docker-compose

BUILD_NUMER ?= $(shell date +%s)

export COMPOSE_PROJECT_NAME=grapi-test-$(BUILD_NUMBER)

# CI

.PHONY: test-backend-kopano-ci-run
test-backend-kopano-ci-run:
	$(DOCKERCOMPOSE) up -d
	$(DOCKERCOMPOSE) run --rm kopano_grapi_test /workspace/test/starttest.sh

.PHONY: test-backend-kopano-ci-clean
test-backend-kopano-ci-clean:
	$(DOCKERCOMPOSE) down -v || true
