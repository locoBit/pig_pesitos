PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
COMPOSE ?= docker compose
ALEMBIC ?= alembic

.PHONY: install install-dev db-up db-down db-reset db-logs migrate run db-upgrade db-revision test test-coverage

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

db-upgrade:
	$(ALEMBIC) upgrade head

db-revision:
	$(ALEMBIC) revision -m "${NAME}"

run:
	$(PYTHON) -m pig_pesitos.bot.app

test:
	$(PYTHON) -m pytest

test-coverage:
	coverage run -m pytest
	coverage report -m
