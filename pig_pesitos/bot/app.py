import logging
import os

from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters

from pig_pesitos.config import ConfigError, get_bot_token, get_database_url
from pig_pesitos.utils.monitoring import init_sentry
from pig_pesitos.constants import AMOUNT, CATEGORY, CONCEPT, LIMIT_AMOUNT, REPORT_PERIOD, REPORT_TYPE, FORGET_CONFIRM
from pig_pesitos.bot.handlers import BotHandlers
from pig_pesitos.repositories.database import DatabaseError, DatabaseManager
from pig_pesitos.services.expense_service import ExpenseService
from pig_pesitos.services.report_service import ReportService


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    level=getattr(logging, LOG_LEVEL, logging.INFO),
)
logger = logging.getLogger(__name__)


async def log_error(update, context) -> None:  # type: ignore[no-untyped-def]
    """Global error handler for unexpected exceptions in Telegram handlers."""

    # Avoid logging full update contents to keep logs privacy-friendly
    user_id = None
    if update and getattr(update, "effective_user", None):
        user_id = update.effective_user.id  # type: ignore[union-attr]

    logger.exception(
        "Unhandled error in handler [user=%s]: %s",
        user_id,
        getattr(context, "error", None),
    )


def build_application() -> Application:
    init_sentry()

    db = DatabaseManager(get_database_url())
    try:
        db.initialize()
    except DatabaseError as error:
        raise SystemExit(f"Database initialization failed: {error}") from error

    handlers = BotHandlers(ExpenseService(db), ReportService(db))
    application = Application.builder().token(get_bot_token()).build()
    application.add_error_handler(log_error)

    expense_conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("gasto", handlers.expense_command)],
        states={
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.amount_input)],
            CONCEPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.concept_input)],
            CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.category_input)],
        },
        fallbacks=[CommandHandler("cancelar", handlers.cancel)],
    )
    report_conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("reporte", handlers.report_command)],
        states={
            REPORT_PERIOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.report_period_input)],
            REPORT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.report_type_input)],
        },
        fallbacks=[CommandHandler("cancelar", handlers.cancel)],
    )
    limit_conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("limite", handlers.limit_command)],
        states={
            LIMIT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.limit_amount_input)],
        },
        fallbacks=[CommandHandler("cancelar", handlers.cancel)],
    )
    forget_conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("olvidame", handlers.forget_me)],
        states={
            FORGET_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.forget_me_confirm)],
        },
        fallbacks=[CommandHandler("cancelar", handlers.cancel)],
    )

    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("cancelar", handlers.cancel))
    application.add_handler(expense_conversation_handler)
    application.add_handler(report_conversation_handler)
    application.add_handler(limit_conversation_handler)
    application.add_handler(forget_conversation_handler)
    return application


def main() -> None:
    try:
        application = build_application()
    except ConfigError as error:
        raise SystemExit(str(error)) from error
    application.run_polling()


if __name__ == "__main__":
    main()
