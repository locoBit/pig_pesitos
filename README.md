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

```bash
python3 -m pip install -r requirements.txt
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

## Environment variables

- `TELEGRAM_BOT_TOKEN`: Telegram bot token
- `DATABASE_URL`: PostgreSQL connection string
- `SQLITE_DB_PATH`: path to the legacy SQLite database for migration

## Notes

- Do not commit `.env` or database files
- `.env.example` should only contain placeholder values
- If the bot token was ever hardcoded before, rotate it in BotFather before using the bot again
