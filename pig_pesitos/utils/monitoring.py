from __future__ import annotations

import logging
import os

import sentry_sdk


logger = logging.getLogger(__name__)


def init_sentry() -> None:
    """Initialize Sentry error monitoring if a DSN is configured.

    This is intentionally minimal: it only reports unhandled exceptions. If
    `SENTRY_DSN` is not set, this function is a no-op.
    """

    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        logger.info("Sentry DSN not configured; error monitoring disabled")
        return

    environment = os.getenv("SENTRY_ENVIRONMENT", "development").strip() or "development"

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        traces_sample_rate=0.0,  # we only care about errors for this bot
    )
    logger.info("Sentry initialized for environment '%s'", environment)
