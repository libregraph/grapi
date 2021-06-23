DOCKER := docker
IMAGE_NAME := mysql:5.7
CONTAINER_NAME  := kc-dev-db
NETWORK_NAME := kc-dev-network

.PHONY: build
build:
	@echo "[$(CONTAINER_NAME)] Pulling image..."
	$(DOCKER) pull $(IMAGE_NAME)

.PHONY: start
start:
ifeq ($(shell $(DOCKER) ps -a --format '{{.Names}}' --filter "name=$(CONTAINER_NAME)"), $(CONTAINER_NAME))
	@echo "[$(CONTAINER_NAME)] Starting the container...";
	$(DOCKER) start $(CONTAINER_NAME);
else
	@echo "[$(CONTAINER_NAME)] Creating a new container...";
	$(DOCKER) run --name $(CONTAINER_NAME) -p 3306:3306/tcp \
		-e MYSQL_ROOT_PASSWORD=kopano-dev \
		-e MYSQL_USER=kopano-dev-user \
		-e MYSQL_PASSWORD=kopano-dev \
		-e MYSQL_DATABASE=kopano_dev_1 \
		-v $(PWD)/mysql/conf.d/kopano-dev.cnf:/etc/mysql/conf.d/kopano-dev.cnf:ro \
		-d $(IMAGE_NAME) \
		--network $(NETWORK_NAME)
endif

.PHONY: clean
clean:
	@echo "[$(CONTAINER_NAME)] Removing container..."
	$(DOCKER) rm -f $(CONTAINER_NAME)
