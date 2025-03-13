.PHONY : venv build run package install-docs run-docs

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
	pip install mkdocs==1.6.0 mkdocs-material==9.5.32

run-docs: install-docs
	mkdocs serve