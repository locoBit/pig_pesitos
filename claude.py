import logging
import os
import sqlite3
import re
import tempfile
import uuid
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import pendulum

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    REPORT_PDF_ENABLED = True
except ImportError:
    REPORT_PDF_ENABLED = False

conn = sqlite3.connect('expense_data.db')
cursor = conn.cursor()

# Create table if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS expense (
        user_id REAL,
        amount REAL,
        concept TEXT,
        category INTEGER,
        timestamp TEXT,
        PRIMARY KEY (user_id, timestamp)
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS monthly_limit (
        user_id REAL PRIMARY KEY,
        limit_amount REAL NOT NULL,
        updated_at TEXT NOT NULL
    )
''')
conn.commit()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def _start_request(context: ContextTypes.DEFAULT_TYPE) -> str:
    request_id = uuid.uuid4().hex
    context.chat_data["request_id"] = request_id
    return request_id


def _get_request_id(context: ContextTypes.DEFAULT_TYPE) -> str:
    request_id = context.chat_data.get("request_id")
    if not request_id:
        request_id = _start_request(context)
    return request_id


def _end_request(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.chat_data.pop("request_id", None)

# Define conversation states
AMOUNT = 0
CONCEPT = 1
CATEGORY = 2
REPORT_PERIOD = 0
REPORT_TYPE = 1
LIMIT_AMOUNT = 3

# Lista oficial de categorías de gasto
VALID_CATEGORIES = [
    "transporte",
    "vestimenta",
    "alimentos",
    "entretenimiento",
    "servicios",
    "salud",
    "otros",
]

REPORT_PERIODS = {
    "day": "el día de hoy", 
    "week": "esta semana", 
    "month": "este mes", 
}

REPORT_TYPES = {
    "percentage": "porcentajes", 
    "detail": "detallado", 
}


def _get_period_range(report_period: str) -> tuple[str, str]:
    now = pendulum.now()

    if report_period == "week":
        start = now.start_of('week')
        end = now.end_of('week')
    elif report_period == "month":
        start = now.start_of('month')
        end = now.end_of('month')
    else:
        start = now.start_of('day')
        end = now.end_of('day')

    return start.to_datetime_string(), end.to_datetime_string()


def _get_monthly_limit(user_id: int) -> float | None:
    cursor.execute(
        'SELECT limit_amount FROM monthly_limit WHERE user_id = ?',
        (user_id,)
    )
    row = cursor.fetchone()
    return row[0] if row else None


def _format_monthly_limit(limit_value: float | None) -> str:
    return f"${limit_value:.2f}" if limit_value is not None else "No definido"


def _build_pdf_report(rows, period_label, limit_text):
    if not REPORT_PDF_ENABLED:
        logger.warning(
            "No se pudo generar el PDF: la librería 'reportlab' no está instalada."
        )
        return None

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp_file.close()
    pdf_path = tmp_file.name

    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter
    margin = 40
    y_position = height - margin

    headers = ["#", "Monto", "Concepto", "Categoría", "Fecha"]
    column_widths = [30, 80, 150, 120, 140]

    def draw_page_header():
        nonlocal y_position
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin, y_position, f"Reporte detallado ({period_label})")
        y_position -= 25
        c.setFont("Helvetica", 11)
        c.drawString(margin, y_position, f"Límite mensual: {limit_text}")
        y_position -= 20
        draw_row(headers, bold=True, skip_check=True)

    def draw_row(values, bold=False, skip_check=False):
        nonlocal y_position
        if not skip_check and y_position < margin + 40:
            c.showPage()
            y_position = height - margin
            draw_page_header()
        c.setFont("Helvetica-Bold" if bold else "Helvetica", 10)
        x = margin
        for value, width_col in zip(values, column_widths):
            c.drawString(x, y_position, str(value))
            x += width_col
        y_position -= 18

    draw_page_header()

    total_amount = 0.0
    for idx, (amount, concept, category, timestamp) in enumerate(rows, start=1):
        draw_row([
            idx,
            f"${amount:.2f}",
            concept,
            category.capitalize(),
            timestamp
        ])
        total_amount += amount

    draw_row(["", "", "", "Total", f"${total_amount:.2f}"], bold=True)

    c.save()
    return pdf_path


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    request_id = _start_request(context)
    user = update.effective_user
    logger.info("[%s][user=%s] /start command invoked", request_id, user.id)
    await update.message.reply_text(
        f"Hola {user.first_name}! Soy Pig Pesitos, el bot que te ayudará a registrar tus gastos. Déjame ayudarte a crecer en tus finanzas personales. 🐷 oink! \n\n"
        f"Usa /gasto para agregar un nuevo gasto.\n"
        f"Usa /reporte para ver tus reportes.\n"
        f"Usa /limite para definir un límite de gastos mensual.\n"
        f"Usa /cancelar en cualquier comento para cancelar la operación"
    )
    _end_request(context)

async def expense_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the expense conversation and ask for amount."""
    request_id = _start_request(context)
    user_id = update.effective_user.id
    logger.info("[%s][user=%s] Inicio de captura de gasto", request_id, user_id)
    await update.message.reply_text(
        "Vamos a agregar un nuevo gasto. Por favor escribe el monto (solo números, ejemplo: 25.99):"
    )
    return AMOUNT

async def amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Validate and store the amount, then ask for concept."""
    request_id = _get_request_id(context)
    user_id = update.effective_user.id
    text = update.message.text.strip()
    logger.info("[%s][user=%s] Validando monto ingresado: %s", request_id, user_id, text)
    
    # Amount validation regex pattern (allows numbers with optional decimal point)
    amount_pattern = r'^\d+(\.\d{1,2})?$'
    
    if not re.match(amount_pattern, text):
        logger.warning("[%s][user=%s] Monto inválido", request_id, user_id)
        await update.message.reply_text(
            "Formato inválido del monto. Por favor escribe un número positivo con máximo dos decimales (ejemplo: 12.50):"
        )
        return AMOUNT
    
    try:
        amount = float(text)
        if amount <= 0:
            logger.warning("[%s][user=%s] Monto no positivo", request_id, user_id)
            await update.message.reply_text("Por favor escribe un número positivo mayor a cero:")
            return AMOUNT
        
        if amount > 1000000:  # Reasonability check
            logger.warning("[%s][user=%s] Monto excede límite permitido", request_id, user_id)
            await update.message.reply_text(
                "El monto es demasiado alto. El monto máximo permitido es 1,000,000:"
            )
            return AMOUNT
            
        # Store the amount in user context
        context.user_data['amount'] = amount
        logger.info("[%s][user=%s] Monto válido almacenado: %.2f", request_id, user_id, amount)
        
        await update.message.reply_text(
            f"Monto: ${amount:.2f}\n"
            f"Por favor escribe el concepto o descripción del gasto (máximo 15 caracteres):"
        )
        return CONCEPT
        
    except ValueError:
        logger.exception("[%s][user=%s] Error convirtiendo monto", request_id, user_id)
        await update.message.reply_text("Número inválido. Por favor escribe el monto de nuevo:")
        return AMOUNT

async def concept_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Validate and store the concept, then ask for category."""
    request_id = _get_request_id(context)
    user_id = update.effective_user.id
    concept = update.message.text.strip()
    logger.info("[%s][user=%s] Validando concepto: %s", request_id, user_id, concept)
    
    # Validate concept length
    if len(concept) > 15:
        logger.warning("[%s][user=%s] Concepto demasiado largo", request_id, user_id)
        await update.message.reply_text(
            f"Concepto demasiado largo ({len(concept)}/15 caracteres). Por favor escribe una descripción mas corta:"
        )
        return CONCEPT
    
    # Validate concept has only valid characters (including acentos y eñe)
    if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\s\-_.,]+$', concept):
        logger.warning("[%s][user=%s] Concepto con caracteres inválidos", request_id, user_id)
        await update.message.reply_text(
            "El concepto contiene caracteres inválidos. Usa solo letras (incluyendo acentos), números, espacios, guiones, puntos o comas:"
        )
        return CONCEPT
    
    # Store concept in user context
    context.user_data['concept'] = concept
    logger.info("[%s][user=%s] Concepto aceptado", request_id, user_id)
    
    # Get the stored amount
    amount = context.user_data['amount']
    
    # Create keyboard with category buttons
    keyboard = [[cat.capitalize()] for cat in sorted(VALID_CATEGORIES)]
    reply_markup = ReplyKeyboardMarkup(
        keyboard, 
        one_time_keyboard=True,
        resize_keyboard=True
    )
    
    await update.message.reply_text(
        f"Monto: ${amount:.2f}\n"
        f"Concepto: {concept}\n"
        f"Por favor selecciona una categoría:",
        reply_markup=reply_markup
    )
    return CATEGORY

async def category_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Validate and store the category, then save the complete expense."""
    request_id = _get_request_id(context)
    user_id = update.effective_user.id
    category = update.message.text.strip().lower()
    logger.info("[%s][user=%s] Categoría recibida: %s", request_id, user_id, category)
    
    # Get the stored amount and concept
    amount = context.user_data['amount']
    concept = context.user_data['concept']
    
    # Basic category validation
    if category not in VALID_CATEGORIES:
        logger.warning("[%s][user=%s] Categoría inválida: %s", request_id, user_id, category)
        # Create keyboard with category buttons
        keyboard = [[cat.capitalize()] for cat in sorted(VALID_CATEGORIES)]
        reply_markup = ReplyKeyboardMarkup(
            keyboard, 
            one_time_keyboard=True,
            resize_keyboard=True
        )
        
        await update.message.reply_text(
            "Por favor selecciona una categoría válida de las sugeridas:",
            reply_markup=reply_markup
        )
        return CATEGORY
    
    # Insert the expense amount with concept, category, and timestamp in the database
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('''
        INSERT INTO expense (user_id, amount, concept, category, timestamp) 
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, amount, concept, category.lower(), timestamp))
    conn.commit()
    logger.info(
        "[%s][user=%s] Gasto almacenado: monto=%.2f concepto=%s categoría=%s",
        request_id,
        user_id,
        amount,
        concept,
        category
    )

    # Calculate total spent in this category
    # TODO add the today filter
    cursor.execute('SELECT SUM(amount) FROM expense WHERE user_id = ? AND category = ?', (user_id, category.lower()))
    category_total = cursor.fetchone()[0]
    
    await update.message.reply_text(
        f"✅ El gasto se agregó exitosamente!\n"
        f"Monto: ${amount:.2f}\n"
        f"Concepto: {concept}\n"
        f"Categoría: {category.capitalize()}\n\n"
        f"Total gastado en {category}: ${category_total:.2f}\n\n"
        f"Para agregar otro gasto, usa /gasto otra vez.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Clear user data
    context.user_data.clear()
    _end_request(context)
    logger.info("[%s][user=%s] Registro de gasto completado", request_id, user_id)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the expense entry."""
    request_id = _get_request_id(context)
    user_id = update.effective_user.id
    logger.info("[%s][user=%s] Operación cancelada por el usuario", request_id, user_id)
    context.user_data.clear()
    await update.message.reply_text(
        "El gasto fue cancelado. Usa /gasto para iniciar otra vez.",
        reply_markup=ReplyKeyboardRemove()
    )
    _end_request(context)
    return ConversationHandler.END


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    request_id = _start_request(context)
    user_id = update.effective_user.id
    logger.info("[%s][user=%s] Inicio de flujo de reportes", request_id, user_id)
    keyboard = [[label.capitalize()] for idx, (key, label) in enumerate(REPORT_PERIODS.items())]
    reply_markup = ReplyKeyboardMarkup(
        keyboard, 
        one_time_keyboard=True,
        resize_keyboard=True
    )
    
    await update.message.reply_text(
        f"Por favor selecciona un periodo:",
        reply_markup=reply_markup
    )
    return REPORT_PERIOD

async def report_period_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    request_id = _get_request_id(context)
    user_id = update.effective_user.id
    report_period_label = update.message.text.strip().lower()
    logger.info("[%s][user=%s] Periodo seleccionado: %s", request_id, user_id, report_period_label)
    report_period = dict(map(reversed, REPORT_PERIODS.items())).get(report_period_label)

    if not report_period:
        logger.warning("[%s][user=%s] Periodo inválido: %s", request_id, user_id, report_period_label)
        keyboard = [[label.capitalize()] for idx, (key, label) in enumerate(REPORT_PERIODS.items())]
        reply_markup = ReplyKeyboardMarkup(
            keyboard, 
            one_time_keyboard=True,
            resize_keyboard=True
        )
        
        await update.message.reply_text(
            f"Por favor selecciona un periodo válido:",
            reply_markup=reply_markup
        )

        return REPORT_PERIOD

    context.user_data['report_period'] = report_period 
    logger.info("[%s][user=%s] Periodo aceptado: %s", request_id, user_id, report_period)

    keyboard = [[label.capitalize()] for label in sorted(REPORT_TYPES.values())]
    reply_markup = ReplyKeyboardMarkup(
        keyboard, 
        one_time_keyboard=True,
        resize_keyboard=True
    )

    await update.message.reply_text(
        "Por favor selecciona un tipo de reporte:",
        reply_markup=reply_markup
    )

    return REPORT_TYPE


async def report_type_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    request_id = _get_request_id(context)
    user_id = update.effective_user.id
    report_type_label = update.message.text.strip().lower()
    logger.info("[%s][user=%s] Tipo de reporte solicitado: %s", request_id, user_id, report_type_label)
    report_type = dict(map(reversed, REPORT_TYPES.items())).get(report_type_label)

    if not report_type:
        logger.warning("[%s][user=%s] Tipo de reporte inválido: %s", request_id, user_id, report_type_label)
        keyboard = [[label.capitalize()] for label in sorted(REPORT_TYPES.values())]
        reply_markup = ReplyKeyboardMarkup(
            keyboard, 
            one_time_keyboard=True,
            resize_keyboard=True
        )

        await update.message.reply_text(
            "Por favor selecciona un tipo de reporte válido de los sugeridos:",
            reply_markup=reply_markup
        )
        return REPORT_TYPE

    report_period = context.user_data['report_period']
    period_label = REPORT_PERIODS.get(report_period, report_period)
    start_range, end_range = _get_period_range(report_period)

    if report_type == "percentage":
        await percentage_report(update, context, start_range, end_range, period_label, request_id)
    elif report_type == "detail":
        await detailed_report(update, context, start_range, end_range, period_label, request_id)
    else:
        logger.error("[%s][user=%s] Tipo de reporte no soportado: %s", request_id, user_id, report_type)
        await update.message.reply_text(
            "Tipo de reporte no soportado aún."
        )

    context.user_data.clear()
    _end_request(context)
    return ConversationHandler.END

async def percentage_report(update: Update, context: ContextTypes.DEFAULT_TYPE, start_range: str, end_range: str, period_label: str, request_id: str) -> None:
    """Show the percentage distribution of expenses for a given period."""
    user_id = update.effective_user.id
    logger.info(
        "[%s][user=%s] Generando reporte porcentual (%s)",
        request_id,
        user_id,
        period_label
    )

    cursor.execute('''
        SELECT amount, concept, category, timestamp FROM expense
        WHERE user_id = ? AND timestamp BETWEEN ? AND ?
    ''', (user_id, start_range, end_range))

    user_expenses = cursor.fetchall()
    monthly_limit = _get_monthly_limit(user_id)
    limit_text = _format_monthly_limit(monthly_limit)
    logger.info(
        "[%s][user=%s] %d gastos encontrados para reporte porcentual",
        request_id,
        user_id,
        len(user_expenses)
    )

    if user_expenses:
        categories: dict[str, float] = {}
        expenses_sum = 0.0
        for amount, concept, category, timestamp in user_expenses:
            expenses_sum += amount
            categories[category] = categories.get(category, 0.0) + amount
        
        message = f"📊 *Reporte porcentual ({period_label})*\n\n"
        sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        
        for category, amount in sorted_categories:
            percentage = (amount / expenses_sum) * 100
            message += f"*{category.capitalize()}*: ${amount:.2f} ({percentage:.1f}%)\n"
        
        message += f"\n*Total del periodo*: ${expenses_sum:.2f}"
        message += f"\n*Límite mensual*: {limit_text}"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        logger.info("[%s][user=%s] Reporte porcentual enviado", request_id, user_id)
    else:
        await update.message.reply_text(
            f"No tienes registrado ningún gasto para {period_label}. Usa /gasto para agregar uno.\n"
            f"Límite mensual: {limit_text}"
        )
        logger.info("[%s][user=%s] Reporte porcentual sin datos", request_id, user_id)
        return


async def detailed_report(update: Update, context: ContextTypes.DEFAULT_TYPE, start_range: str, end_range: str, period_label: str, request_id: str) -> None:
    """Show a tabular detailed report for the selected period."""
    user_id = update.effective_user.id
    logger.info(
        "[%s][user=%s] Generando reporte detallado (%s)",
        request_id,
        user_id,
        period_label
    )

    cursor.execute('''
        SELECT amount, concept, category, timestamp FROM expense
        WHERE user_id = ? AND timestamp BETWEEN ? AND ?
        ORDER BY timestamp ASC
    ''', (user_id, start_range, end_range))

    rows = cursor.fetchall()
    monthly_limit = _get_monthly_limit(user_id)
    limit_text = _format_monthly_limit(monthly_limit)
    logger.info(
        "[%s][user=%s] %d gastos encontrados para reporte detallado",
        request_id,
        user_id,
        len(rows)
    )

    if not rows:
        await update.message.reply_text(
            f"No encontramos gastos para {period_label}. Usa /gasto para agregar uno.\n"
            f"Límite mensual: {limit_text}"
        )
        logger.info("[%s][user=%s] Reporte detallado sin datos", request_id, user_id)
        return

    headers = [("#", 4), ("Monto", 12), ("Concepto", 18), ("Categoría", 15), ("Fecha", 20)]
    header_format = " ".join([f"{{:<{width}}}" for _, width in headers])
    separator = " ".join(['-' * width for _, width in headers])

    response = f"Reporte detallado ({period_label})\n\n"
    response += header_format.format(*[header for header, _ in headers]) + "\n"
    response += separator + "\n"

    total = 0.0
    for idx, (amount, concept, category, timestamp) in enumerate(rows, start=1):
        response += header_format.format(
            idx,
            f"${amount:.2f}",
            concept[:18],
            category.capitalize(),
            timestamp
        ) + "\n"
        total += amount

    response += separator
    response += f"\nTotal del periodo: ${total:.2f}"
    response += f"\nLímite mensual: {limit_text}"
    response += "\n\n📱 Tip: gira tu teléfono o descarga el PDF adjunto para ver todo el detalle."

    await update.message.reply_text(f"```{response}```", parse_mode='Markdown')

    try:
        pdf_path = _build_pdf_report(rows, period_label, limit_text)
        if pdf_path:
            filename = f"reporte_detallado_{period_label.replace(' ', '_')}.pdf"
            with open(pdf_path, 'rb') as pdf_file:
                await update.message.reply_document(
                    document=pdf_file,
                    filename=filename,
                    caption="Aquí tienes el PDF con todo el detalle."
                )
            logger.info("[%s][user=%s] PDF de reporte detallado enviado", request_id, user_id)
        else:
            raise RuntimeError("PDF builder no disponible")
    except Exception as error:
        logger.exception(
            "[%s][user=%s] Error generando PDF del reporte detallado: %s",
            request_id,
            user_id,
            error
        )
        await update.message.reply_text(
            "⚠️ El reporte no pudo ser generado, hemos reportado este error al administrador."
        )
    finally:
        if 'pdf_path' in locals() and pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)


async def limit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    request_id = _start_request(context)
    user_id = update.effective_user.id
    logger.info("[%s][user=%s] Inicio de configuración de límite mensual", request_id, user_id)
    await update.message.reply_text(
        "Vamos a definir tu límite mensual de gastos. Por favor escribe el monto en pesos (ejemplo: 2500.50):"
    )
    return LIMIT_AMOUNT


async def limit_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    request_id = _get_request_id(context)
    user_id = update.effective_user.id
    text = update.message.text.strip()
    logger.info("[%s][user=%s] Validando límite mensual ingresado: %s", request_id, user_id, text)

    amount_pattern = r'^\d+(\.\d{1,2})?$'
    if not re.match(amount_pattern, text):
        logger.warning("[%s][user=%s] Formato inválido para límite", request_id, user_id)
        await update.message.reply_text(
            "Formato inválido. Escribe un número positivo con máximo dos decimales (ejemplo: 1250.75):"
        )
        return LIMIT_AMOUNT

    amount = float(text)

    if amount <= 0:
        logger.warning("[%s][user=%s] Límite no positivo", request_id, user_id)
        await update.message.reply_text("El monto debe ser mayor a cero. Intenta nuevamente:")
        return LIMIT_AMOUNT

    if amount >= 100000:
        logger.warning("[%s][user=%s] Límite fuera de rango", request_id, user_id)
        await update.message.reply_text("El límite debe ser menor a $100,000.00. Intenta nuevamente:")
        return LIMIT_AMOUNT

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('''
        INSERT INTO monthly_limit (user_id, limit_amount, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            limit_amount = excluded.limit_amount,
            updated_at = excluded.updated_at
    ''', (user_id, amount, timestamp))
    conn.commit()
    logger.info("[%s][user=%s] Límite mensual actualizado: %.2f", request_id, user_id, amount)

    await update.message.reply_text(
        f"✅ Tu límite mensual quedó establecido en ${amount:.2f}. Puedes actualizarlo cuando quieras usando /limite."
    )
    _end_request(context)
    return ConversationHandler.END


def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token("8043472961:AAGjfA10rbimk2DAYANl14LBo5PYGWofjsc").build()

    # Add conversation handler for expense tracking
    expense_conversation_handler = ConversationHandler(
        entry_points=[
            CommandHandler("gasto", expense_command),
        ],
        states={
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_input)],
            CONCEPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, concept_input)],
            CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, category_input)],
        },
        fallbacks=[CommandHandler("cancelar", cancel)],
    )
    report_conversation_handler = ConversationHandler(
        entry_points=[
            CommandHandler("reporte", report_command)
        ],
        states={
            REPORT_PERIOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_period_input)],
            REPORT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_type_input)],
        },
        fallbacks=[CommandHandler("cancelar", cancel)],
    )

    limit_conversation_handler = ConversationHandler(
        entry_points=[
            CommandHandler("limite", limit_command)
        ],
        states={
            LIMIT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, limit_amount_input)],
        },
        fallbacks=[CommandHandler("cancelar", cancel)],
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancelar", cancel))
    application.add_handler(expense_conversation_handler)
    application.add_handler(report_conversation_handler)
    application.add_handler(limit_conversation_handler)

    # Start the Bot
    application.run_polling()

if __name__ == "__main__":
    main()