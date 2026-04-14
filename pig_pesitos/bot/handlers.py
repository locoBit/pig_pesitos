import logging
import os

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes, ConversationHandler

from pig_pesitos.constants import (
    AMOUNT,
    CATEGORY,
    CONCEPT,
    LIMIT_AMOUNT,
    REPORT_PERIOD,
    REPORT_PERIODS,
    REPORT_TYPE,
    REPORT_TYPES,
    VALID_CATEGORIES,
    FORGET_CONFIRM,
)
from pig_pesitos.services.expense_service import ExpenseService
from pig_pesitos.services.report_service import ReportService
from pig_pesitos.repositories.database import DatabaseError
from pig_pesitos.utils.reporting import build_pdf_report, format_timestamp
from pig_pesitos.utils.request import end_request, get_request_id, start_request
from pig_pesitos.validators import is_valid_category, validate_amount, validate_concept, validate_limit_amount


logger = logging.getLogger(__name__)


def format_monthly_limit(limit_value: float | None) -> str:
    return f"${limit_value:.2f}" if limit_value is not None else "No definido"


def build_category_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [[cat.capitalize()] for cat in sorted(VALID_CATEGORIES)]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)


def build_period_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [[label.capitalize()] for label in REPORT_PERIODS.values()]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)


def build_report_type_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [[label.capitalize()] for label in sorted(REPORT_TYPES.values())]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)


class BotHandlers:
    def __init__(self, expense_service: ExpenseService, report_service: ReportService):
        self.expense_service = expense_service
        self.report_service = report_service

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        request_id = start_request(context)
        user = update.effective_user
        logger.info("[%s][user=%s] /start command invoked", request_id, user.id)
        await update.message.reply_text(
            f"Hola {user.first_name}! Soy Pig Pesitos, el bot que te ayudará a registrar tus gastos. Déjame ayudarte a crecer en tus finanzas personales. 🐷 oink! \n\n"
            f"Usa /gasto para agregar un nuevo gasto.\n"
            f"Usa /reporte para ver tus reportes.\n"
            f"Usa /limite para definir un límite de gastos mensual.\n"
            f"Usa /cancelar en cualquier comento para cancelar la operación"
        )
        end_request(context)

    async def expense_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        request_id = start_request(context)
        user_id = update.effective_user.id
        logger.info("[%s][user=%s] Inicio de captura de gasto", request_id, user_id)
        await update.message.reply_text(
            "Vamos a agregar un nuevo gasto. Por favor escribe el monto (solo números, ejemplo: 25.99):"
        )
        return AMOUNT

    async def amount_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        request_id = get_request_id(context)
        user_id = update.effective_user.id
        text = update.message.text.strip()
        logger.info("[%s][user=%s] Validando monto ingresado: %s", request_id, user_id, text)

        is_valid, error_message, amount = validate_amount(text)
        if not is_valid:
            logger.warning("[%s][user=%s] Monto inválido", request_id, user_id)
            await update.message.reply_text(error_message)
            return AMOUNT

        context.user_data["amount"] = amount
        logger.info("[%s][user=%s] Monto válido almacenado: %.2f", request_id, user_id, amount)
        await update.message.reply_text(
            f"Monto: ${amount:.2f}\n"
            f"Por favor escribe el concepto o descripción del gasto (máximo 15 caracteres):"
        )
        return CONCEPT

    async def concept_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        request_id = get_request_id(context)
        user_id = update.effective_user.id
        concept = update.message.text.strip()
        logger.info("[%s][user=%s] Validando concepto: %s", request_id, user_id, concept)

        is_valid, error_message = validate_concept(concept)
        if not is_valid:
            logger.warning("[%s][user=%s] Concepto inválido", request_id, user_id)
            await update.message.reply_text(error_message)
            return CONCEPT

        context.user_data["concept"] = concept
        amount = context.user_data["amount"]
        logger.info("[%s][user=%s] Concepto aceptado", request_id, user_id)
        await update.message.reply_text(
            f"Monto: ${amount:.2f}\n"
            f"Concepto: {concept}\n"
            f"Por favor selecciona una categoría:",
            reply_markup=build_category_keyboard(),
        )
        return CATEGORY

    async def category_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        request_id = get_request_id(context)
        user_id = update.effective_user.id
        category = update.message.text.strip().lower()
        logger.info("[%s][user=%s] Categoría recibida: %s", request_id, user_id, category)

        amount = context.user_data["amount"]
        concept = context.user_data["concept"]
        if not is_valid_category(category):
            logger.warning("[%s][user=%s] Categoría inválida: %s", request_id, user_id, category)
            await update.message.reply_text(
                "Por favor selecciona una categoría válida de las sugeridas:",
                reply_markup=build_category_keyboard(),
            )
            return CATEGORY

        try:
            category_total = self.expense_service.create_expense(user_id, amount, concept, category)
        except DatabaseError:
            logger.exception("[%s][user=%s] Error al guardar el gasto", request_id, user_id)
            await update.message.reply_text(
                "⚠️ No pudimos guardar tu gasto por un problema temporal con la base de datos. "
                "Intenta nuevamente más tarde."
            )
            end_request(context)
            return ConversationHandler.END

        logger.info(
            "[%s][user=%s] Gasto almacenado: monto=%.2f concepto=%s categoría=%s",
            request_id,
            user_id,
            amount,
            concept,
            category,
        )
        await update.message.reply_text(
            f"✅ El gasto se agregó exitosamente!\n"
            f"Monto: ${amount:.2f}\n"
            f"Concepto: {concept}\n"
            f"Categoría: {category.capitalize()}\n\n"
            f"Total gastado en {category}: ${category_total:.2f}\n\n"
            f"Para agregar otro gasto, usa /gasto otra vez.",
            reply_markup=ReplyKeyboardRemove(),
        )
        context.user_data.clear()
        end_request(context)
        logger.info("[%s][user=%s] Registro de gasto completado", request_id, user_id)
        return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        request_id = get_request_id(context)
        user_id = update.effective_user.id
        logger.info("[%s][user=%s] Operación cancelada por el usuario", request_id, user_id)
        context.user_data.clear()
        await update.message.reply_text(
            "El gasto fue cancelado. Usa /gasto para iniciar otra vez.",
            reply_markup=ReplyKeyboardRemove(),
        )
        end_request(context)
        return ConversationHandler.END

    async def report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        request_id = start_request(context)
        user_id = update.effective_user.id
        logger.info("[%s][user=%s] Inicio de flujo de reportes", request_id, user_id)
        await update.message.reply_text(
            "Por favor selecciona un periodo:",
            reply_markup=build_period_keyboard(),
        )
        return REPORT_PERIOD

    async def report_period_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        request_id = get_request_id(context)
        user_id = update.effective_user.id
        report_period_label = update.message.text.strip().lower()
        logger.info("[%s][user=%s] Periodo seleccionado: %s", request_id, user_id, report_period_label)
        report_period = dict(map(reversed, REPORT_PERIODS.items())).get(report_period_label)
        if not report_period:
            logger.warning("[%s][user=%s] Periodo inválido: %s", request_id, user_id, report_period_label)
            await update.message.reply_text(
                "Por favor selecciona un periodo válido:",
                reply_markup=build_period_keyboard(),
            )
            return REPORT_PERIOD

        context.user_data["report_period"] = report_period
        logger.info("[%s][user=%s] Periodo aceptado: %s", request_id, user_id, report_period)
        await update.message.reply_text(
            "Por favor selecciona un tipo de reporte:",
            reply_markup=build_report_type_keyboard(),
        )
        return REPORT_TYPE

    async def report_type_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        request_id = get_request_id(context)
        user_id = update.effective_user.id
        report_type_label = update.message.text.strip().lower()
        logger.info("[%s][user=%s] Tipo de reporte solicitado: %s", request_id, user_id, report_type_label)
        report_type = dict(map(reversed, REPORT_TYPES.items())).get(report_type_label)
        if not report_type:
            logger.warning("[%s][user=%s] Tipo de reporte inválido: %s", request_id, user_id, report_type_label)
            await update.message.reply_text(
                "Por favor selecciona un tipo de reporte válido de los sugeridos:",
                reply_markup=build_report_type_keyboard(),
            )
            return REPORT_TYPE

        report_period = context.user_data["report_period"]
        if report_type == "percentage":
            await self.percentage_report(update, user_id, report_period, request_id)
        elif report_type == "detail":
            await self.detailed_report(update, user_id, report_period, request_id)
        else:
            logger.error("[%s][user=%s] Tipo de reporte no soportado: %s", request_id, user_id, report_type)
            await update.message.reply_text("Tipo de reporte no soportado aún.")

        context.user_data.clear()
        end_request(context)
        return ConversationHandler.END

    async def percentage_report(self, update: Update, user_id: int, report_period: str, request_id: str) -> None:
        try:
            expenses, period_label, monthly_limit = self.report_service.get_percentage_report_data(user_id, report_period)
        except DatabaseError:
            logger.exception("[%s][user=%s] Error al obtener datos para reporte porcentual", request_id, user_id)
            await update.message.reply_text(
                "⚠️ No pudimos obtener tu reporte por un problema temporal con la base de datos. "
                "Intenta nuevamente más tarde."
            )
            return
        limit_text = format_monthly_limit(monthly_limit)
        logger.info("[%s][user=%s] %d gastos encontrados para reporte porcentual", request_id, user_id, len(expenses))
        if not expenses:
            await update.message.reply_text(
                f"No tienes registrado ningún gasto para {period_label}. Usa /gasto para agregar uno.\n"
                f"Límite mensual: {limit_text}"
            )
            return

        categories: dict[str, float] = {}
        expenses_sum = 0.0
        for expense in expenses:
            amount = float(expense.amount)
            expenses_sum += amount
            categories[expense.category] = categories.get(expense.category, 0.0) + amount

        message = f"📊 *Reporte porcentual ({period_label})*\n\n"
        for category, amount in sorted(categories.items(), key=lambda item: item[1], reverse=True):
            percentage = (amount / expenses_sum) * 100
            message += f"*{category.capitalize()}*: ${amount:.2f} ({percentage:.1f}%)\n"
        message += f"\n*Total del periodo*: ${expenses_sum:.2f}"
        message += f"\n*Límite mensual*: {limit_text}"
        await update.message.reply_text(message, parse_mode="Markdown")

    async def detailed_report(self, update: Update, user_id: int, report_period: str, request_id: str) -> None:
        try:
            rows, period_label, monthly_limit = self.report_service.get_detailed_report_data(user_id, report_period)
        except DatabaseError:
            logger.exception("[%s][user=%s] Error al obtener datos para reporte detallado", request_id, user_id)
            await update.message.reply_text(
                "⚠️ No pudimos obtener tu reporte detallado por un problema temporal con la base de datos. "
                "Intenta nuevamente más tarde."
            )
            return
        limit_text = format_monthly_limit(monthly_limit)
        logger.info("[%s][user=%s] %d gastos encontrados para reporte detallado", request_id, user_id, len(rows))
        if not rows:
            await update.message.reply_text(
                f"No encontramos gastos para {period_label}. Usa /gasto para agregar uno.\n"
                f"Límite mensual: {limit_text}"
            )
            return

        headers = [("#", 4), ("Monto", 12), ("Concepto", 18), ("Categoría", 15), ("Fecha", 20)]
        header_format = " ".join(f"{{:<{width}}}" for _, width in headers)
        separator = " ".join("-" * width for _, width in headers)
        response = f"Reporte detallado ({period_label})\n\n"
        response += header_format.format(*[header for header, _ in headers]) + "\n"
        response += separator + "\n"
        total = 0.0
        for idx, row in enumerate(rows, start=1):
            amount = float(row.amount)
            response += header_format.format(
                idx,
                f"${amount:.2f}",
                row.concept[:18],
                row.category.capitalize(),
                format_timestamp(row.timestamp),
            ) + "\n"
            total += amount

        response += separator
        response += f"\nTotal del periodo: ${total:.2f}"
        response += f"\nLímite mensual: {limit_text}"
        response += "\n\n📱 Tip: gira tu teléfono o descarga el PDF adjunto para ver todo el detalle."
        await update.message.reply_text(f"```{response}```", parse_mode="Markdown")

        try:
            pdf_path = build_pdf_report(rows, period_label, limit_text)
            if not pdf_path:
                raise RuntimeError("PDF builder no disponible")
            filename = f"reporte_detallado_{period_label.replace(' ', '_')}.pdf"
            with open(pdf_path, "rb") as pdf_file:
                await update.message.reply_document(
                    document=pdf_file,
                    filename=filename,
                    caption="Aquí tienes el PDF con todo el detalle.",
                )
        except Exception as error:
            logger.exception(
                "[%s][user=%s] Error generando PDF del reporte detallado: %s",
                request_id,
                user_id,
                error,
            )
            await update.message.reply_text(
                "⚠️ El reporte no pudo ser generado, hemos reportado este error al administrador."
            )
        finally:
            if "pdf_path" in locals() and pdf_path and os.path.exists(pdf_path):
                os.remove(pdf_path)

    async def limit_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        request_id = start_request(context)
        user_id = update.effective_user.id
        logger.info("[%s][user=%s] Inicio de configuración de límite mensual", request_id, user_id)
        await update.message.reply_text(
            "Vamos a definir tu límite mensual de gastos. Por favor escribe el monto en pesos (ejemplo: 2500.50):"
        )
        return LIMIT_AMOUNT

    async def limit_amount_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        request_id = get_request_id(context)
        user_id = update.effective_user.id
        text = update.message.text.strip()
        logger.info("[%s][user=%s] Validando límite mensual ingresado: %s", request_id, user_id, text)
        is_valid, error_message, amount = validate_limit_amount(text)
        if not is_valid:
            logger.warning("[%s][user=%s] Formato inválido para límite", request_id, user_id)
            await update.message.reply_text(error_message)
            return LIMIT_AMOUNT

        try:
            self.expense_service.set_monthly_limit(user_id, amount)
        except DatabaseError:
            logger.exception("[%s][user=%s] Error al actualizar el límite mensual", request_id, user_id)
            await update.message.reply_text(
                "⚠️ No pudimos actualizar tu límite mensual por un problema temporal. "
                "Intenta nuevamente más tarde."
            )
            end_request(context)
            return ConversationHandler.END

        logger.info("[%s][user=%s] Límite mensual actualizado: %.2f", request_id, user_id, amount)
        await update.message.reply_text(
            f"✅ Tu límite mensual quedó establecido en ${amount:.2f}. Puedes actualizarlo cuando quieras usando /limite."
        )
        end_request(context)
        return ConversationHandler.END

    async def forget_me(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Entry point for the /olvidame flow.

        Asks for an explicit confirmation before deleting any data.
        """

        request_id = start_request(context)
        user_id = update.effective_user.id
        logger.info("[%s][user=%s] Inicio de flujo /olvidame", request_id, user_id)

        keyboard = ReplyKeyboardMarkup(
            [["Sí, borrar todo", "No, cancelar"]],
            one_time_keyboard=True,
            resize_keyboard=True,
        )
        await update.message.reply_text(
            "⚠️ Esta acción borrará *todos* tus gastos y tu límite mensual asociados a este chat. "
            "No habrá forma de recuperar esta información más adelante.\n\n"
            "Si estás seguro, elige *Sí, borrar todo*.",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
        return FORGET_CONFIRM

    async def forget_me_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Confirmation step for /olvidame.

        Only performs the deletion when the user explicitly confirms.
        """

        request_id = get_request_id(context)
        user_id = update.effective_user.id
        response = update.message.text.strip().lower()
        logger.info("[%s][user=%s] Respuesta de confirmación /olvidame: %s", request_id, user_id, response)

        if response not in {"sí, borrar todo", "si, borrar todo", "no, cancelar"}:
            await update.message.reply_text(
                "Por favor selecciona una de las opciones disponibles.",
                reply_markup=ReplyKeyboardMarkup(
                    [["Sí, borrar todo", "No, cancelar"]],
                    one_time_keyboard=True,
                    resize_keyboard=True,
                ),
            )
            return FORGET_CONFIRM

        if response in {"no, cancelar"}:
            logger.info("[%s][user=%s] Usuario canceló la eliminación de datos", request_id, user_id)
            await update.message.reply_text(
                "Perfecto, no borramos nada. Tus datos siguen intactos.",
                reply_markup=ReplyKeyboardRemove(),
            )
            end_request(context)
            return ConversationHandler.END

        # User confirmed deletion
        try:
            self.expense_service.delete_user_data(user_id)
        except DatabaseError:
            logger.exception("[%s][user=%s] Error al eliminar los datos del usuario", request_id, user_id)
            await update.message.reply_text(
                "⚠️ No pudimos borrar tus datos por un problema temporal con la base de datos. "
                "Intenta nuevamente más tarde.",
                reply_markup=ReplyKeyboardRemove(),
            )
            end_request(context)
            return ConversationHandler.END

        await update.message.reply_text(
            "✅ Listo. Borramos todos tus gastos y tu límite mensual asociados a este chat. "
            "No podremos recuperar esta información más adelante.",
            reply_markup=ReplyKeyboardRemove(),
        )
        end_request(context)
        return ConversationHandler.END
