PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
COMPOSE ?= docker compose

.PHONY: install install-dev db-up db-down db-reset db-logs migrate run

install:
	$(PIP) install -e .

install-dev:
	$(PIP) install -e .[dev]

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
	$(PYTHON) -m pig_pesitos.bot.app
