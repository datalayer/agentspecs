# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

SHELL=/bin/bash

.DEFAULT_GOAL := default

.PHONY: clean build test

VERSION = "0.0.3"

default: all ## Default target is all.

help: ## display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

all: clean dev ## Clean Install and Build

install:
	pip install .

dev:
	pip install ".[test,lint,typing]"

build:
	pip install build
	python -m build .

clean: ## clean
	git clean -fdx

test: ## Run tests
	python -m pytest tests/ -v

start-agent: ## Start the MCP agent CLI (stdio server). Usage: make start-agent [MODEL=<model>]
	python examples/agent/agent_cli.py $(if $(MODEL),--model $(MODEL),)

start-agentspecs: ## Start the Agentspecs agent CLI (stdio server). Usage: make start-agentspecs [MODEL=<model>]
	python examples/agent/agent_cli.py --codemode $(if $(MODEL),--model $(MODEL),)

build-docker:
	docker buildx build --platform linux/amd64,linux/arm64 -t datalayer/agentspecs:${VERSION} .
	docker image tag datalayer/agentspecs:${VERSION} datalayer/agentspecs:latest

start-docker:
	docker run -i --rm \
	  -e SERVER_URL=http://localhost:8888 \
	  -e TOKEN=MY_TOKEN \
	  -e NOTEBOOK_PATH=notebook.ipynb \
	  --network=host \
	  datalayer/agentspecs:latest

pull-docker:
	docker image pull datalayer/agentspecs:latest

push-docker:
	docker push datalayer/agentspecs:${VERSION}
	docker push datalayer/agentspecs:latest

claude-linux:
	NIXPKGS_ALLOW_UNFREE=1 nix run github:k3d3/claude-desktop-linux-flake \
		--impure \
		--extra-experimental-features flakes \
		--extra-experimental-features nix-command

jupyterlab:
	pip uninstall -y pycrdt datalayer_pycrdt
	pip install datalayer_pycrdt
	jupyter lab \
		--port 8888 \
		--ip 0.0.0.0 \
		--ServerApp.root_dir ./dev/content \
		--IdentityProvider.token MY_TOKEN

publish-pypi: # publish the pypi package
	git clean -fdx && \
		python -m build
	@exec echo
	@exec echo twine upload ./dist/*-py3-none-any.whl
	@exec echo
	@exec echo https://pypi.org/project/agentspecs/#history
