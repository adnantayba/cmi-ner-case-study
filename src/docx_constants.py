"""Patterns and rule tables for docx entity extraction."""

from __future__ import annotations

from collections.abc import Callable

# --- Value-shape heuristics (regex) ---
DATE_PATTERNS: tuple[str, ...] = (
    r"\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}",
    r"\d{1,2}/\d{1,2}/\d{2,4}",
    r"\d{4}-\d{2}-\d{2}",
)

CURRENCY_PATTERNS: tuple[str, ...] = (
    r"(?:EUR|USD|GBP|JPY|CHF)\s+\d+(?:\.\d+)?\s*(?:million|billion|thousand|M|B|K)?",
    r"[€$£]\s?\d+(?:[.,]\d+)?\s*(?:million|billion|M|B)?",
)

PERCENTAGE_PATTERNS: tuple[str, ...] = (r"\d+(?:\.\d+)?\s*%",)

ISIN_PATTERN = r"[A-Z]{2}[A-Z0-9]{9}[0-9]"

# --- Key/value line parsing ---
KV_SEPARATORS: tuple[str, ...] = (
    r"\s*:\s*",
    r"\s*=\s*",
    r"\s*-\s*",
    r"\s*–\s*",
)

KV_KEY_MAX_LEN = 50

# --- Label → entity field (order matters; optional guard on normalized key) ---
KeyFieldRule = tuple[str, tuple[str, ...], Callable[[str], bool] | None]

KEY_FIELD_RULES: list[KeyFieldRule] = [
    ("Counterparty", ("party", "counterparty", "cp"), None),
    ("InitialValuationDate", ("initial valuation", "initial val", "pricing date"), None),
    ("ValuationDate", ("valuation date", "val date"), lambda k: "initial" not in k),
    ("Maturity", ("maturity", "termination date", "end date"), None),
    ("Notional", ("notional", "nominal", "face value"), None),
    ("Underlying", ("underlying", "reference asset", "linked to"), None),
    ("Coupon", ("coupon", "interest rate", "rate"), None),
    ("Barrier", ("barrier", "knock", "trigger"), None),
    ("Calendar", ("calendar", "business day", "day count"), None),
]
