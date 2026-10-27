.PHONY: help setup-venv setup-tests setup-docs build run package docs run-test test integration-test modinput-tests

APP_VERSION := $$(cat globalConfig.json | jq -r '.meta.version')
APP_NAME := $$(cat globalConfig.json | jq -r '.meta.name')

PYTHON_PATH := $(shell pyenv which python3.9 2>/dev/null || command -v python3.9 || command -v python3)
VENV_COMMAND := $(PYTHON_PATH) -m venv

VENV := .venv
VENV_PYTHON := $(VENV)/bin/python
PYTEST_COMMAND := $(VENV_PYTHON) -m pytest
UCC_GEN := $(VENV)/bin/ucc-gen

OUTPUT_PATH := output
OUTPUT_BUILD_PATH := $(OUTPUT_PATH)/$(APP_NAME)

GENESYSCLOUD_HOSTNAME ?= localhost
GENESYSCLOUD_PORT ?= 3004

SPLUNK_READY := Ansible playbook complete, will begin streaming splunkd_stderr.log

MODINPUT_TEST_PREPARE ?= true
RUN_PREPARE ?= true

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

help:
	@cat $(MAKEFILE_LIST) | python3 -c "$$PRINT_HELP_PYSCRIPT"

# ── Environment Setup ──────────────────────────

setup-venv: ## Create Python virtual environment
	$(VENV_COMMAND) $(VENV)
	$(VENV_PYTHON) -m pip install --upgrade splunk-add-on-ucc-framework

setup-tests: ## Setup tests virtual environment
	$(VENV_COMMAND) $(VENV)
	$(VENV_PYTHON) -m pip install -r tests/test-requirements.txt

setup-docs: ## Setup docs virtual environment
	$(VENV_COMMAND) $(VENV)
	$(VENV_PYTHON) -m pip install mkdocs==1.6.0 mkdocs-material==9.5.32 mkdocs-print-site-plugin==2.6.0

# ── Build ──────────────────────────

build: setup-venv ## Build with UCC
	$(UCC_GEN) build --ta-version=$(APP_VERSION);

package: build ## Build and package with UCC
	mkdir -p dist
	$(UCC_GEN) package --path $(OUTPUT_BUILD_PATH) -o dist

docs: setup-docs ## Build docs with mkdocs
	mkdocs serve

# ── Docker Development ─────────────────────────

run: ## Run add-on in docker container
	$(RUN_PREPARE)
	@if [ -f "docker-compose.yml" ]; then \
		( \
			export APP_NAME=$(APP_NAME); \
			docker compose up -d; \
			echo "Waiting for Splunk to be ready..."; \
			START=$$(date +%s); until docker logs --since "$$START" gc_splunk 2>&1 | grep -qF "$(SPLUNK_READY)"; do sleep 1; printf "."; done; \
			echo " SPLUNK READY"; \
		); \
	else \
		echo "Skipping: docker-compose.yml file not found"; \
	fi

run-test: build setup-tests ## Run vendor mock and add-on in docker container
	$(RUN_PREPARE)
	@if [ -f "etc/cicd/inputs.conf" ]; then \
		( \
			mkdir -p $(OUTPUT_BUILD_PATH)/local; \
			cp etc/cicd/inputs.conf $(OUTPUT_BUILD_PATH)/local; \
		); \
	else \
		echo "Error: etc/cicd/inputs.conf file not found" && exit 1; \
	fi
	@if [ -f "tests/vendor/docker-compose.yml" ]; then \
		( \
			export APP_NAME=$(APP_NAME); \
			export COMPOSE_FILE=tests/vendor/docker-compose.yml; \
			docker compose up -d; \
			echo "Waiting for Splunk to be ready..."; \
			START=$$(date +%s); until docker logs --since "$$START" gc_splunk 2>&1 | grep -qF "$(SPLUNK_READY)"; do sleep 1; printf "."; done; \
			echo " SPLUNK READY"; \
		); \
	else \
		echo "Skipping: tests/vendor/docker-compose.yml file not found" && exit 1; \
	fi

# ── Tests ─────────────────────────

test: ## Run default test suite (integration tests)

integration-test: run-test ## Run integration tests
	@if [ -d "tests/integration" ]; then \
		( \
			export GENESYSCLOUD_HOST="http://$(GENESYSCLOUD_HOSTNAME):$(GENESYSCLOUD_PORT)" && \
			$(PYTEST_COMMAND) tests/integration \
		); \
	else \
		echo "Skipping: tests/integration directory not found"; \
	fi

modinput-tests: run-test ## Run modinput functional tests
	$(MODINPUT_TEST_PREPARE)
	@if [ -d "tests/modinput_functional" ]; then \
		( \
			$(PYTEST_COMMAND) tests/modinput_functional \
		); \
	else \
		echo "Skipping: tests/modinput_functional directory not found"; \
	fi
