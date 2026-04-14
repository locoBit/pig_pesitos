import logging

from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters

from pig_pesitos.config import ConfigError, get_bot_token, get_database_url
from pig_pesitos.constants import AMOUNT, CATEGORY, CONCEPT, LIMIT_AMOUNT, REPORT_PERIOD, REPORT_TYPE
from pig_pesitos.bot.handlers import BotHandlers
from pig_pesitos.repositories.database import DatabaseManager
from pig_pesitos.services.expense_service import ExpenseService
from pig_pesitos.services.report_service import ReportService


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


def build_application() -> Application:
    db = DatabaseManager(get_database_url())
    db.initialize()
    handlers = BotHandlers(ExpenseService(db), ReportService(db))
    application = Application.builder().token(get_bot_token()).build()

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

    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("cancelar", handlers.cancel))
    application.add_handler(expense_conversation_handler)
    application.add_handler(report_conversation_handler)
    application.add_handler(limit_conversation_handler)
    return application


def main() -> None:
    try:
        application = build_application()
    except ConfigError as error:
        raise SystemExit(str(error)) from error
    application.run_polling()
