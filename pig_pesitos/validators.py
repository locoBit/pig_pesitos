import re

from pig_pesitos.constants import (
    AMOUNT_PATTERN,
    CONCEPT_PATTERN,
    MAX_AMOUNT,
    MAX_CONCEPT_LENGTH,
    MAX_LIMIT_AMOUNT,
    VALID_CATEGORIES,
)


def validate_amount(text: str) -> tuple[bool, str | None, float | None]:
    value = text.strip()
    if not re.match(AMOUNT_PATTERN, value):
        return (
            False,
            (
                "Formato inválido del monto. Por favor escribe un número positivo "
                "con máximo dos decimales (ejemplo: 12.50):"
            ),
            None,
        )

    amount = float(value)
    if amount <= 0:
        return False, "Por favor escribe un número positivo mayor a cero:", None
    if amount > MAX_AMOUNT:
        return (
            False,
            "El monto es demasiado alto. El monto máximo permitido es 1,000,000:",
            None,
        )
    return True, None, amount


def validate_limit_amount(text: str) -> tuple[bool, str | None, float | None]:
    value = text.strip()
    if not re.match(AMOUNT_PATTERN, value):
        return (
            False,
            (
                "Formato inválido. Escribe un número positivo con máximo dos "
                "decimales (ejemplo: 1250.75):"
            ),
            None,
        )

    amount = float(value)
    if amount <= 0:
        return False, "El monto debe ser mayor a cero. Intenta nuevamente:", None
    if amount >= MAX_LIMIT_AMOUNT:
        return (
            False,
            "El límite debe ser menor a $100,000.00. Intenta nuevamente:",
            None,
        )
    return True, None, amount


def validate_concept(concept: str) -> tuple[bool, str | None]:
    value = concept.strip()
    if len(value) > MAX_CONCEPT_LENGTH:
        return False, (
            f"Concepto demasiado largo ({len(value)}/{MAX_CONCEPT_LENGTH} "
            "caracteres). Por favor escribe una descripción mas corta:"
        )
    if not re.match(CONCEPT_PATTERN, value):
        return False, (
            "El concepto contiene caracteres inválidos. Usa solo letras "
            "(incluyendo acentos), números, espacios, guiones, puntos o comas:"
        )
    return True, None


def is_valid_category(category: str) -> bool:
    return category.strip().lower() in VALID_CATEGORIES
