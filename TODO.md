# TODO

Future tasks for the Pig Pesitos bot so nothing important gets lost in the sauce.

## High priority

- [x] Migrate Telegram bot token to environment variables
  - Remove hardcoded token from `claude.py`
  - Read token from `os.environ`
  - Rotate the exposed token in BotFather immediately
  - Add local development support with `.env` if needed

- [x] Migrate database from SQLite to PostgreSQL
  - Design a proper schema and constraints
  - Replace raw SQLite connection logic with a Postgres-compatible data layer
  - Create a migration plan for existing data from `expense_data.db`
  - Validate date/time handling and indexes for reports

- [ ] Create unit tests
  - Test amount validation
  - Test concept validation
  - Test category validation
  - Test report period calculations
  - Test monthly limit logic
  - Test PDF generation fallback behavior

- [x] Improve code structure
  - Split bot handlers, database access, validation, and reporting into separate modules
  - Remove duplicated logic and enforce DRY
  - Introduce a service/repository structure instead of putting everything in one file
  - Keep files cohesive and under control in size
  - Add central configuration management

- [x] Create GitHub repository
  - Initialize repo hygiene
  - Add `.gitignore`
  - Prevent committing secrets and database files
  - Configure branch protection later if collaboration grows

- [x] Create `README.md`
  - Project description
  - Features
  - Local setup instructions
  - Environment variables
  - Running the bot
  - Testing instructions
  - Deployment notes

- [ ] Create a web page
  - Define the goal: landing page, dashboard, or marketing page
  - Show product purpose and bot features
  - Add installation/contact/help info
  - Consider future authenticated dashboard for reports and account settings

## Strongly recommended for production readiness

- [x] Fix secret exposure and security hygiene
  - Rotate the currently exposed Telegram token
  - Add `.env` and `.gitignore`
  - Never commit tokens, credentials, or database files
  - Use environment variables for all secrets

- [x] Add dependency management
  - Create `requirements.txt` or `pyproject.toml`
  - Pin dependency versions
  - Separate production and development dependencies if needed

- [ ] Add database migrations
  - Use a migration tool such as Alembic
  - Version schema changes instead of editing tables ad hoc

- [ ] Add logging and monitoring improvements
  - Avoid logging sensitive user data unnecessarily
  - Add structured logs where useful
  - Track bot errors and critical failures
  - Integrate Sentry or similar error monitoring

- [ ] Add automated tests beyond unit tests
  - Integration tests for database interactions
  - Handler-level tests for Telegram flows
  - Regression tests for reports and edge cases

- [ ] Add CI/CD pipeline
  - Run linting and tests on every push
  - Block merges when checks fail
  - Optionally automate deployment

- [ ] Add code quality tooling
  - Formatter: `black` or equivalent
  - Linter: `ruff` or equivalent
  - Type checking: `mypy` if practical

- [x] Improve error handling and resilience
  - Handle database failures gracefully
  - Handle Telegram API errors and timeouts
  - Add retry strategy where appropriate
  - Avoid crashing the whole bot for one bad operation

- [ ] Introduce proper configuration management
  - Centralize settings for token, DB URL, logging, and environment
  - Support `development`, `staging`, and `production`

- [x] Review data privacy concerns
  - Minimize stored personal data
  - Define retention policy for expense records if needed
  - Decide what user identifiers are stored and why
  - Add a privacy notice if this becomes public-facing

- [ ] Add backup and recovery plan
  - Back up production database regularly
  - Test restore procedure
  - Document recovery steps

- [ ] Prepare deployment setup
  - Add deployment instructions for Railway, Render, or Fly.io
  - Define start command/process type
  - Move away from local-only assumptions

- [ ] Consider switching from polling to webhooks later
  - Polling is okay to start
  - Webhooks may be better for scalability and operational efficiency in production

- [ ] Review authorization and abuse protection
  - Decide whether anyone can use the bot or only approved users
  - Add basic rate limiting or abuse protections if the bot becomes public
  - Validate all user input consistently

- [ ] Add admin and operations features
  - Admin alerts for failures
  - Health check command or diagnostic flow
  - Usage metrics and basic analytics

## Nice-to-have

- [ ] Dockerize the application
- [x] Add Makefile or task runner commands
- [ ] Add export features such as CSV in addition to PDF
- [ ] Improve report formatting for mobile readability
- [x] Add budget alerts when user approaches monthly limit
- [ ] Add category management instead of fixed hardcoded categories

## Notes

- Current code has a hardcoded Telegram token in `claude.py`. This is the most urgent issue.
- Current code uses SQLite, which is acceptable for local development but weak for production deployments.
- Main bot logic is concentrated in one large file, which will get painful to maintain over time.
