.PHONY: dev test lint build up down
dev:
	docker compose up --build
test:
	docker run --rm -v "$(CURDIR)/backend/tests:/app/backend/tests:ro" android-server-manager pytest -v backend/tests
lint:
	docker compose run --rm --no-deps android-server-manager ruff check backend/app backend/tests
build:
	docker build --platform linux/amd64 -t android-server-manager .
up:
	docker compose up -d --build
down:
	docker compose down
