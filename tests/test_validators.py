import pytest

from pig_pesitos.validators import (
    is_valid_category,
    validate_amount,
    validate_concept,
    validate_limit_amount,
)


@pytest.mark.parametrize(
    "text, expected_amount",
    [
        ("10", 10.0),
        ("10.5", 10.5),
        ("0.01", 0.01),
    ],
)
def test_validate_amount_happy_path(text: str, expected_amount: float) -> None:
    is_valid, error, amount = validate_amount(text)

    assert is_valid is True
    assert error is None
    assert amount == pytest.approx(expected_amount)


@pytest.mark.parametrize(
    "text",
    ["-1", "0", "abc", "10.999", ""],
)
def test_validate_amount_invalid(text: str) -> None:
    is_valid, error, amount = validate_amount(text)

    assert is_valid is False
    assert error is not None
    assert amount is None


def test_validate_limit_amount_happy_path() -> None:
    is_valid, error, amount = validate_limit_amount("100.50")

    assert is_valid is True
    assert error is None
    assert amount == pytest.approx(100.50)


@pytest.mark.parametrize(
    "text",
    ["-1", "0", "100000.00", "abc"],
)
def test_validate_limit_amount_invalid(text: str) -> None:
    is_valid, error, amount = validate_limit_amount(text)

    assert is_valid is False
    assert error is not None
    assert amount is None


def test_validate_concept_valid() -> None:
    is_valid, error = validate_concept("comida")

    assert is_valid is True
    assert error is None


@pytest.mark.parametrize(
    "concept",
    ["x" * 20, "invalido!@"],
)
def test_validate_concept_invalid(concept: str) -> None:
    is_valid, error = validate_concept(concept)

    assert is_valid is False
    assert error is not None


@pytest.mark.parametrize(
    "category, expected",
    [
        ("alimentos", True),
        (" Alimentos ", True),
        ("ALIMENTOS", True),
        ("desconocida", False),
    ],
)
def test_is_valid_category(category: str, expected: bool) -> None:
    assert is_valid_category(category) is expected
