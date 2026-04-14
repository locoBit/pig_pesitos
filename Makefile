PYTHON ?= python3
COMPOSE ?= docker compose

.PHONY: db-up db-down db-reset db-logs migrate run

db-up:
	$(COMPOSE) up -d

db-down:
	$(COMPOSE) down

db-reset:
	$(COMPOSE) down -v

db-logs:
	$(COMPOSE) logs -f postgres

migrate:
	$(PYTHON) migrate_sqlite_to_postgres.py

run:
	$(PYTHON) claude.py
