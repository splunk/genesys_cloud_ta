.PHONY: venv build run package

APP_VERSION := $$(cat globalConfig.json | jq -r '.meta.version')
APP_NAME := $$(cat globalConfig.json | jq -r '.meta.name')

venv:
	python3 -m venv .venv

build: venv
	source .venv/bin/activate;
	ucc-gen build --ta-version=$(APP_VERSION)

run:
	APP_NAME=$(APP_NAME) docker compose up -d

package: build
	# pandoc README.md -f markdown-implicit_figures -o output/$(APP_NAME)/README.pdf
	cp README.md output/$(APP_NAME)/
	mkdir -p dist
	ucc-gen package --path output/$(APP_NAME) -o dist

install-docs: venv
	source .venv/bin/activate;
	pip install mkdocs==1.6.0 mkdocs-material==9.5.32 mkdocs-print-site-plugin==2.6.0

run-docs: install-docs
	mkdocs serve

install-tests: venv
	source .venv/bin/activate;
	pip install pytest==6.2.4 splunk-sdk

run-tests: install-tests
	cd tests && \
	export GENESYSCLOUD_HOST="http://localhost:3004" && python -m pytest integration/*

run-functional-tests: install-tests
	cd tests;
	python -m pytest tests/modinput_functional/*
