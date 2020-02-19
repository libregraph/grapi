DOCKERCOMPOSE ?= docker-compose
DOCKERCOMPOSE_UP_ARGS ?=
DOCKERCOMPOSE_EXEC_ARGS ?=
EXTRA_LOCAL_ADMIN_USER ?=

BUILD_TAG ?= $(shell date +%s)

export COMPOSE_PROJECT_NAME=grapi-test-$(BUILD_TAG)
export EXTRA_LOCAL_ADMIN_USER

# CI

.PHONY: test-backend-kopano-ci-run
test-backend-kopano-ci-run:
	$(DOCKERCOMPOSE) up -d $(DOCKERCOMPOSE_UP_ARGS)
	$(DOCKERCOMPOSE) exec $(DOCKERCOMPOSE_EXEC_ARGS) kopano_grapi_test /workspace/test/starttest.sh

.PHONY: test-backend-kopano-ci-clean
test-backend-kopano-ci-clean:
	$(DOCKERCOMPOSE) down -v || true
