APP_NAME := $(shell python scripts/metadata.py name)
APP_VERSION := $(shell python scripts/metadata.py version)
IMAGE_NAME := demsking/$(APP_NAME)

COMPOSE_SERVICES := ollama

.PHONY: help install run test docker-build docker-run docker-stop docker-logs clean

shell:
	tmuxinator

stop:
	tmux kill-session -t oremi-isinmi-agent

up: pull
	docker compose up -d $(COMPOSE_SERVICES) --remove-orphans

logs:
	docker compose logs -f

down:
	docker compose down $(COMPOSE_SERVICES)

stats:
	docker compose stats

help:
	@echo "Oremi Isinmi Agent - Available commands"
	@echo "  install          Install dependencies with uv"
	@echo "  run              Run the application"
	@echo "  test             Run tests"
	@echo "  docker-build     Build Docker image"
	@echo "  docker-run       Run Docker container"
	@echo "  docker-stop      Stop Docker container"
	@echo "  clean            Clean temporary files"

install:
	rm -rf .venv
	uv venv --python 3.12
	uv sync

tests:
	uv run pytest tests/ -v

coverage:
	uv run pytest --cov=server

coverage-html:
	uv run pytest --cov=server --cov-report=html

lint:
	pre-commit run --all-files

fix:
	ruff check . --fix

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov


#
## Packaging
build/context:
	@if ! docker buildx inspect $(APP_NAME) > /dev/null 2>&1; then \
		docker buildx create --name $(APP_NAME) --bootstrap; \
	fi
	mkdir -p build/
	touch $@

image: build/context
	@echo "Building $(IMAGE_NAME):$(APP_VERSION)"
	uv lock
	docker buildx use $(APP_NAME)
	docker buildx build . \
	  --platform linux/amd64,linux/arm64 \
	  --push \
	  --progress plain \
	  --tag $(IMAGE_NAME):$(APP_VERSION) \
	  --tag $(IMAGE_NAME):latest \
	  --label "org.opencontainers.image.title=$(APP_NAME)" \
	  --label "org.opencontainers.image.description=$(shell python scripts/metadata.py description)" \
	  --label "org.opencontainers.image.version=$(APP_VERSION)" \
	  --label "org.opencontainers.image.revision=$(shell git rev-parse HEAD)" \
	  --label "org.opencontainers.image.authors=Sébastien Demanou <demsking@gmail.com>" \
	  --label "org.opencontainers.image.created=$(shell date --rfc-3339=seconds)" \
	  --label "org.opencontainers.image.vendor=Sébastien Demanou" \
	  --label "org.opencontainers.image.licenses=$(shell python scripts/metadata.py license)"

image-test:
	docker build . \
	  --progress plain \
	  --tag $(IMAGE_NAME):test

live: image-test
	docker run -it --rm --env-file .env.example demsking/oremi-isinmi-agent:test

publish: image-test
	git tag v$(APP_VERSION)
	$(MAKE) image
	git push --tags origin main
