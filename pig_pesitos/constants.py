AMOUNT = 0
CONCEPT = 1
CATEGORY = 2
REPORT_PERIOD = 10
REPORT_TYPE = 11
LIMIT_AMOUNT = 20

VALID_CATEGORIES = (
    "transporte",
    "vestimenta",
    "alimentos",
    "entretenimiento",
    "servicios",
    "salud",
    "otros",
)

REPORT_PERIODS = {
    "day": "el día de hoy",
    "week": "esta semana",
    "month": "este mes",
}

REPORT_TYPES = {
    "percentage": "porcentajes",
    "detail": "detallado",
}

MAX_AMOUNT = 1_000_000
MAX_LIMIT_AMOUNT = 100_000
MAX_CONCEPT_LENGTH = 15
AMOUNT_PATTERN = r"^\d+(\.\d{1,2})?$"
CONCEPT_PATTERN = r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\s\-_.,]+$"
