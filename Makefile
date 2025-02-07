.PHONY : build run package

APP_VERSION = $$(cat globalConfig.json | jq -r '.meta.version')
APP_NAME=genesys_cloud_ta

build:
	ucc-gen build --ta-version=$(APP_VERSION)

run:
	APP_NAME=$(APP_NAME) docker compose up -d

package: build
	# pandoc README.md -f markdown-implicit_figures -o output/$(APP_NAME)/README.pdf
	cp README.md output/$(APP_NAME)/
	mkdir -p dist
	ucc-gen package --path output/$(APP_NAME) -o dist
