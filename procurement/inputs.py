"""Parse transport values once; business operations receive immutable typed input."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from werkzeug.datastructures import MultiDict

from .errors import DomainError

CATEGORIES = ("Equipment", "Office supplies", "IT infrastructure", "Services", "Other")
MAX_TOTAL = 1_000_000_000_000


def integer(value: object, label: str, minimum: int = 1, maximum: int = 100_000_000_000) -> int:
    if not re.fullmatch(r"[0-9]{1,15}", str(value)):
        raise DomainError(f"{label} must be a whole number.")
    number = int(str(value))
    if not minimum <= number <= maximum:
        raise DomainError(f"{label} must be between {minimum:,} and {maximum:,}.")
    return number


def text(
    data: Mapping[str, str], key: str, label: str, maximum: int = 500, required: bool = True
) -> str:
    value = data.get(key, "").strip()
    if required and not value:
        raise DomainError(f"{label} is required.")
    if len(value) > maximum:
        raise DomainError(f"{label} must be at most {maximum} characters.")
    return value


@dataclass(frozen=True)
class LineInput:
    name: str
    unit: str
    quantity: int
    unit_price: int


@dataclass(frozen=True)
class RequestInput:
    title: str
    category: str
    priority: str
    needed_by: str
    purpose: str
    lines: tuple[LineInput, ...]


def parse_request(data: MultiDict[str, str]) -> RequestInput:
    title = text(data, "title", "Title", 120)
    purpose = text(data, "purpose", "Business purpose", 2000)
    category = text(data, "category", "Category", 40)
    priority = text(data, "priority", "Priority", 10)
    if category not in CATEGORIES or priority not in {"low", "normal", "high"}:
        raise DomainError("Choose a valid category and priority.")
    try:
        needed_by = date.fromisoformat(text(data, "needed_by", "Required date", 10))
    except ValueError:
        raise DomainError("Required date must be a valid date.") from None
    if needed_by < date.today():
        raise DomainError("Required date cannot be in the past.")
    names, quantities, prices = (
        data.getlist(key) for key in ("item_name", "quantity", "unit_price")
    )
    units = data.getlist("unit") or ["unit"] * len(names)
    if (
        not 1 <= len(names) <= 20
        or len({len(names), len(quantities), len(prices), len(units)}) != 1
    ):
        raise DomainError("Include between 1 and 20 complete line items.")
    lines = []
    for name, unit, quantity, price in zip(names, units, quantities, prices):
        if not 1 <= len(name.strip()) <= 160 or not 1 <= len(unit.strip()) <= 30:
            raise DomainError("Item names need 1-160 characters; units need 1-30 characters.")
        lines.append(
            LineInput(
                name.strip(),
                unit.strip(),
                integer(quantity, "Quantity", maximum=10000),
                integer(price, "Unit price"),
            )
        )
    if sum(line.quantity * line.unit_price for line in lines) > MAX_TOTAL:
        raise DomainError("Total cannot exceed Rp 1 trillion.")
    return RequestInput(title, category, priority, needed_by.isoformat(), purpose, tuple(lines))
