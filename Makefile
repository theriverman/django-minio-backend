.DEFAULT_GOAL := help
.PHONY: local compose migrations reset help

# let's capture arguments provided after 'manage' and prevent make from treating them as targets
args := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
.PHONY: manage $(args)

# then swallow extra goals so they don't run as targets
$(args): %:
	@:

LOCAL_ENV := \
		GH_MINIO_ENDPOINT=play.min.io:9000 \
		GH_MINIO_EXTERNAL_ENDPOINT=play.min.io:9000 \
		GH_MINIO_EXTERNAL_ENDPOINT_USE_HTTPS=true \
		GH_MINIO_ACCESS_KEY=Q3AM3UQ867SPQQA43P2F \
		GH_MINIO_SECRET_KEY=zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG \
		GH_MINIO_USE_HTTPS=true \
		MINIO_REGION=us-east-1 \
		DJANGO_SUPERUSER_USERNAME=admin \
		DJANGO_SUPERUSER_PASSWORD=123123 \
		DJANGO_SUPERUSER_EMAIL=admin@local.test

local: ## bootstrap and run the app against the public MinIO playground
	@set -euo pipefail; \
	export $(LOCAL_ENV); \
	uv sync; \
	uv run manage.py initialize_buckets; \
	uv run manage.py migrate; \
	uv run manage.py collectstatic --noinput; \
	uv run manage.py createsuperuser --noinput; \
	uv run manage.py runserver

compose: ## bootstrap and run the docker compose stack
	@set -euo pipefail; \
	docker compose up -d; \
	docker compose exec web uv run manage.py initialize_buckets; \
	docker compose exec web uv run manage.py collectstatic --noinput

migrations: ## run makemigrations then migrate in the active environment (local or Docker)
	@set -euo pipefail; \
	if docker compose ps --services --filter status=running 2>/dev/null | grep -qx web; then \
		docker compose exec web uv run manage.py makemigrations; \
		docker compose exec web uv run manage.py migrate; \
		docker compose restart web; \
	else \
		uv run manage.py makemigrations; \
		uv run manage.py migrate; \
	fi

shell: ## enter into an interactive Django shell (local or Docker)
	@set -euo pipefail; \
	if docker compose ps --services --filter status=running 2>/dev/null | grep -qx web; then \
		docker compose exec web uv run manage.py shell; \
	else \
		uv run manage.py shell; \
	fi

manage: ## access Django's manage.py commands (local or Docker)
	@set -euo pipefail; \
	if docker compose ps --services --filter status=running 2>/dev/null | grep -qx web; then \
		docker compose exec web uv run manage.py $(args); \
	else \
		uv run manage.py $(args); \
	fi

reset: ## clean up the active environment (local removes venv/db, compose shuts stack down)
	@set -euo pipefail; \
	if docker compose ps --services --filter status=running 2>/dev/null | grep -qx web; then \
		docker compose down; \
		printf 'HINT: Delete the images and volumes manually to free up space\n'; \
	else \
		rm -rf .venv; \
		rm -rf db.sqlite3; \
	fi

help: ## show available targets
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | awk 'BEGIN {FS=":.*?## "}; {printf "%-12s %s\n", $$1, $$2}'
