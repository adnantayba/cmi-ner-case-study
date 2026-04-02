import io
import re
from typing import Any

from docx import Document
from pydantic import BaseModel, ConfigDict

from .docx_constants import (
    CURRENCY_PATTERNS,
    DATE_PATTERNS,
    ISIN_PATTERN,
    KEY_FIELD_RULES,
    KV_KEY_MAX_LEN,
    KV_SEPARATORS,
    PERCENTAGE_PATTERNS,
)
from .entities import FinancialEntities


class ExtractionResult(BaseModel):
    """Docx rule-based extraction: entity values and source lines."""

    model_config = ConfigDict(frozen=True)

    entities: dict[str, str]
    evidence: dict[str, list[str]]

    def to_json_dict(self) -> dict[str, Any]:
        return self.model_dump()


def _looks_like_date(value: str) -> bool:
    return any(re.search(p, value, re.IGNORECASE) for p in DATE_PATTERNS)


def _looks_like_currency(value: str) -> bool:
    return any(re.search(p, value, re.IGNORECASE) for p in CURRENCY_PATTERNS)


def _looks_like_percentage(value: str) -> bool:
    return any(re.search(p, value, re.IGNORECASE) for p in PERCENTAGE_PATTERNS)


def _looks_like_isin(value: str) -> bool:
    return bool(re.search(ISIN_PATTERN, value))


def _normalize_key(key: str) -> str:
    """Clean up key for better matching."""
    k = key.strip().lower()
    # Remove parentheses and their content
    k = re.sub(r"\s*\([^)]*\)", "", k)
    # Replace multiple spaces with single
    k = re.sub(r"\s+", " ", k)
    k = k.replace("\u00a0", " ")
    return k.strip()


def _infer_entity_field(key: str, value: str) -> str | None:
    """Map a key-value pair to a FinancialEntities field name, or None."""
    key_lower = _normalize_key(key)

    for field, terms, guard in KEY_FIELD_RULES:
        if guard is not None and not guard(key_lower):
            continue
        if any(t in key_lower for t in terms):
            return field

    # Fallback: infer from value shape when the label did not match above
    if _looks_like_date(value):
        if "initial" in key_lower or "pricing" in key_lower:
            return "InitialValuationDate"
        if "valuation" in key_lower:
            return "ValuationDate"
        if "termination" in key_lower:
            return "Maturity"
        return None

    if _looks_like_currency(value):
        return "Notional"

    if _looks_like_percentage(value):
        if "coupon" in key_lower or "rate" in key_lower:
            return "Coupon"
        if "barrier" in key_lower:
            return "Barrier"
        return "Coupon"

    if _looks_like_isin(value):
        return "Underlying"

    return None


def _extract_kv_from_line(line: str) -> tuple[str, str] | None:
    """Extract key-value pair using various separators."""
    for sep in KV_SEPARATORS:
        parts = re.split(sep, line, maxsplit=1)
        if len(parts) == 2:
            key, value = parts[0].strip(), parts[1].strip()
            if key and value and len(key) < KV_KEY_MAX_LEN:
                return key, value

    return None


def _iter_doc_content(doc: Document) -> list[str]:
    """Extract all text lines from paragraphs and tables."""
    lines = []

    for p in doc.paragraphs:
        text = (p.text or "").strip()
        if text:
            lines.append(text)

    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if not cells:
                continue
            if len(cells) == 1:
                lines.append(cells[0])
            elif len(cells) == 2:
                lines.append(f"{cells[0]}: {cells[1]}")
            else:
                lines.append(" | ".join(cells))

    return lines


def _extract_from_doc(doc: Document) -> ExtractionResult:
    lines = _iter_doc_content(doc)

    keys = tuple(FinancialEntities.model_fields.keys())
    entities: dict[str, str] = {k: "" for k in keys}
    evidence: dict[str, list[str]] = {k: [] for k in keys}

    for line in lines:
        kv = _extract_kv_from_line(line)
        if not kv:
            continue

        raw_key, raw_value = kv
        field_name = _infer_entity_field(raw_key, raw_value)

        if field_name and not entities[field_name]:  # Only take first occurrence
            entities[field_name] = raw_value
            evidence[field_name].append(line)

    # Remove empty evidence
    evidence = {k: v for k, v in evidence.items() if v}

    return ExtractionResult(entities=entities, evidence=evidence)


def extract_entities_from_docx_bytes(data: bytes) -> ExtractionResult:
    doc = Document(io.BytesIO(data))
    return _extract_from_doc(doc)
