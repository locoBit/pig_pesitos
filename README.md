# Pig Pesitos

Pig Pesitos is a Telegram bot for tracking personal expenses, setting a monthly spending limit, and generating simple reports.

## Features

- Register expenses with amount, concept, and category
- Set a monthly spending limit
- Generate percentage and detailed reports
- Export detailed reports to PDF
- Store data in PostgreSQL
- Migrate legacy data from SQLite

## Requirements

- Python 3.11+
- Docker and Docker Compose

## Local setup

### 1. Create your environment file

Copy the example file and fill in your real bot token:

```bash
cp .env.example .env
```

Set at least these values in `.env`:

```env
TELEGRAM_BOT_TOKEN=your-real-bot-token
DATABASE_URL=postgresql://pigpesitos:pigpesitos@localhost:5432/pig_pesitos
SQLITE_DB_PATH=expense_data.db
```

### 2. Install Python dependencies

Recommended local development install:

```bash
make install-dev
```

Minimal runtime install:

```bash
make install
```

If you prefer plain pip commands:

```bash
python3 -m pip install -e .
python3 -m pip install -e .[dev]  # optional dev tooling
```

### 3. Start PostgreSQL with Docker

```bash
make db-up
```

### 4. Migrate existing SQLite data

```bash
make migrate
```

### 5. Run the bot

```bash
make run
```

## Make commands

- `make install` — install the project and production dependencies
- `make install-dev` — install the project plus development tooling
- `make db-up` — start PostgreSQL
- `make db-down` — stop PostgreSQL
- `make db-reset` — stop PostgreSQL and remove its volume
- `make db-logs` — show PostgreSQL logs
- `make migrate` — migrate SQLite data into PostgreSQL
- `make run` — run the bot

## PostgreSQL Docker setup

The project includes a `docker-compose.yml` file with a local PostgreSQL service:

- host: `localhost`
- port: `5432`
- database: `pig_pesitos`
- user: `pigpesitos`
- password: `pigpesitos`

## Database migrations

The project uses Alembic for schema migrations. Basic workflow:

- Make sure `DATABASE_URL` points to the target PostgreSQL database
- Run all migrations to the latest version:

```bash
make db-upgrade
```

If you need to create a new migration (for example after editing the schema):

```bash
make db-revision NAME="short description of change"
# then edit the generated file under alembic/versions/
make db-upgrade
```

For local hacking and tests you can still rely on the legacy `DatabaseManager.initialize()`
bootstrap, but **production deployments should use Alembic migrations as the source of
truth for the schema**.

## Dependency management

This project now uses `pyproject.toml` as the source of truth for dependency and tooling configuration.

- Production dependencies live in `[project.dependencies]`
- Development-only tools live in `[project.optional-dependencies].dev`
- The bot exposes a console script: `pig-pesitos`
- `requirements.txt` and `requirements-dev.txt` are thin compatibility files for pip-based workflows

For production-oriented installs, prefer installing the package itself instead of manually curating ad-hoc dependency lists.

## Environment variables

- `TELEGRAM_BOT_TOKEN`: Telegram bot token
- `DATABASE_URL`: PostgreSQL connection string
- `SQLITE_DB_PATH`: path to the legacy SQLite database for migration

## Data privacy & retention

This project is primarily intended for personal use and small-scale deployments, but it still tries to be reasonable about privacy:

- **What is stored**
  - Your Telegram numeric `user_id` (no name, username, or phone number)
  - Your expenses: amount, concept, category, and timestamp
  - Your optional monthly spending limit
- **Why it is stored**
  - To separate data between different Telegram users
  - To compute totals and generate reports over time
- **Retention policy**
  - Data is kept until you explicitly delete it or the database is reset
  - You can delete all your data at any time with the `/olvidame` command in the bot
  - Deletion is a **hard delete** at the application level; there is no in-app recovery
- **Logs**
  - Logs include your numeric `user_id` for debugging flows, but avoid storing names or usernames
  - For production setups, you should review and harden logging according to your own policies
- **If you go public**
  - This README section is not a formal legal privacy policy
  - If you expose the bot to the public, you should publish a proper privacy notice that explains who operates the bot, where data is stored, and how users can exercise their rights

## Project structure

```text
pig_pesitos/
├── bot/            # Telegram application wiring and handlers
├── repositories/   # Database access layer
├── services/       # Business logic
├── utils/          # Shared helpers
├── config.py       # Environment-based configuration
├── constants.py    # Conversation states and fixed values
└── validators.py   # Input validation helpers
```

Top-level files such as `claude.py`, `config.py`, and `database_manager.py` are thin compatibility wrappers so existing commands keep working.

## Notes

- Do not commit `.env` or database files
- `.env.example` should only contain placeholder values
- If the bot token was ever hardcoded before, rotate it in BotFather before using the bot again
