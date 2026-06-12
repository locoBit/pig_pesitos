from __future__ import annotations

import logging

import sentry_sdk

from pig_pesitos.config import get_sentry_dsn, get_sentry_environment

logger = logging.getLogger(__name__)


def init_sentry() -> None:
    """Initialize Sentry error monitoring if a DSN is configured.

    This is intentionally minimal: it only reports unhandled exceptions. If
    ``SENTRY_DSN`` is not set, this function is a no-op. Environment naming is
    centralized via :mod:`pig_pesitos.config`.
    """

    dsn = get_sentry_dsn()
    if not dsn:
        logger.info("Sentry DSN not configured; error monitoring disabled")
        return

    environment = get_sentry_environment()

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        traces_sample_rate=0.0,  # we only care about errors for this bot
    )
    logger.info("Sentry initialized for environment '%s'", environment)
