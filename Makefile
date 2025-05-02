VERSION=$(shell ./version.sh)
TESTS_TO_RUN=""
TESTS_OPTS=""
CI_REGISTRY_IMAGE="annie-god-father"
COVERAGE_DIR ?= /tmp/coverage-annie-god-father
COVERAGE_FILE ?= ${COVERAGE_DIR}/.coverage

# HELP
.PHONY: help tests

help: ## This help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.DEFAULT_GOAL := help


# CLEAN

clean: clean-build clean-pyc clean-pycache ## Clean repository

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +

clean-pycache:
	find . -name '__pycache__' -exec rm -rf {} +


# TOOLS

lint: clean ## Lint
	pre-commit run -a

proto: ## Generate proto files
	python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. anniegodfather/proto/anniegodfather.proto

# DOCKER

# Build the container
build: lint ## Build the container
	docker build -t $(CI_REGISTRY_IMAGE) .

build-nc: lint ## Build the container without caching
	docker build --no-cache -t $(CI_REGISTRY_IMAGE) .

release: build-nc publish ## Make a release by building and publishing the `{version}` ans `latest` tagged containers to ECR


# Docker publish
publish: repo-login publish-latest publish-version ## Publish the `{version}` ans `latest` tagged containers to ECR

publish-latest: tag-latest ## Publish the `latest` taged container to ECR
	@echo 'publish latest to $(CI_REGISTRY_IMAGE)'
	docker push $(CI_REGISTRY_IMAGE):latest

publish-version: tag-version ## Publish the `{version}` taged container to ECR
	@echo 'publish $(VERSION) to $(CI_REGISTRY_IMAGE)'
	docker push $(CI_REGISTRY_IMAGE):$(VERSION)


# Docker tagging
tag: tag-latest tag-version ## Generate container tags for the `{version}` ans `latest` tags

tag-latest: ## Generate container `{version}` tag
	@echo 'create tag latest'
	docker tag $(CI_REGISTRY_IMAGE) $(CI_REGISTRY_IMAGE):latest

tag-version: ## Generate container `latest` tag
	@echo 'create tag $(VERSION)'
	docker tag $(CI_REGISTRY_IMAGE) $(CI_REGISTRY_IMAGE):$(VERSION)


# VERSIONS

bump-patch: lint tests ## Bump patch version
	bumpversion patch

bump-minor: lint tests ## Bump minor version
	bumpversion minor

bump-major: lint tests ## Bump major version
	bumpversion major


# HELPERS

version: ## Output the current version
	@echo $(VERSION)
