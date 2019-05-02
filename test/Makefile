DOCKERCOMPOSE ?= docker-compose

# CI

.PHONY: test-backend-kopano-ci-run
test-backend-kopano-ci-run:
	$(DOCKERCOMPOSE) up -d
	$(DOCKERCOMPOSE) run --rm kopano_grapi_test /workspace/test/starttest.sh
	$(DOCKERCOMPOSE) down -v
