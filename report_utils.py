import logging
import tempfile
from datetime import datetime

import pendulum

from database_manager import ExpenseRecord

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    REPORT_PDF_ENABLED = True
except ImportError:
    REPORT_PDF_ENABLED = False


logger = logging.getLogger(__name__)


def format_timestamp(timestamp: datetime) -> str:
    return pendulum.instance(timestamp).in_timezone("UTC").format("YYYY-MM-DD HH:mm:ss")


def build_pdf_report(rows: list[ExpenseRecord], period_label: str, limit_text: str):
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

    def draw_row(values, *, bold=False, skip_check=False):
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
    for idx, row in enumerate(rows, start=1):
        amount = float(row.amount)
        draw_row(
            [
                idx,
                f"${amount:.2f}",
                row.concept,
                row.category.capitalize(),
                format_timestamp(row.timestamp),
            ]
        )
        total_amount += amount

    draw_row(["", "", "", "Total", f"${total_amount:.2f}"], bold=True)
    c.save()
    return pdf_path
