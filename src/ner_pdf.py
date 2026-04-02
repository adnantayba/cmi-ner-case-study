from __future__ import annotations

import io
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import pdfplumber
from agno.agent import Agent
from agno.models.together import Together
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict

from .entities import FinancialEntities

load_dotenv()

logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")

TOGETHER_MODEL_ID = "openai/gpt-oss-20b"
DEFAULT_MAX_CHARS = 4000

NER_PROMPT_TEMPLATE = """Extract financial entities from the following document text.
Return null for any field not found.

Document:
{text}"""


class PdfExtractionResult(BaseModel):
    """LLM-based PDF NER; same JSON shape as docx (entities + evidence)."""

    model_config = ConfigDict(frozen=True)

    entities: dict[str, str]
    evidence: dict[str, list[str]]

    def to_json_dict(self) -> dict[str, Any]:
        return self.model_dump()


def extract_pdf_text_from_bytes(data: bytes, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    """Extract plain text from PDF bytes (truncated to max_chars)."""
    text_parts: list[str] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    text = "\n".join(text_parts).strip()
    if len(text) > max_chars:
        text = text[:max_chars]
    return text.strip()


def extract_pdf_text(pdf_path: str, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    """Extract plain text from a PDF file on disk."""
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    return extract_pdf_text_from_bytes(path.read_bytes(), max_chars=max_chars)


def _financial_entities_to_api_entities(fe: FinancialEntities) -> dict[str, str]:
    """Match docx semantics: missing values are empty strings, all keys present."""
    raw = fe.model_dump()
    return {k: ("" if v is None else str(v)) for k, v in raw.items()}


def _build_agent(api_key: str) -> Agent:
    return Agent(
        model=Together(
            id=TOGETHER_MODEL_ID,
            api_key=api_key,
            temperature=0.1,
            max_tokens=500,
            top_p=0.95,
        ),
        description="Financial document analyzer for entity extraction",
        output_schema=FinancialEntities,
        use_json_mode=True,
    )


def extract_entities_from_pdf_bytes(
    data: bytes,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> PdfExtractionResult:
    """
    Run PDF text extraction and Together/Agno NER. Raises ValueError for config/input issues.
    """
    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key:
        raise ValueError("TOGETHER_API_KEY is not set")

    doc_text = extract_pdf_text_from_bytes(data, max_chars=max_chars)
    if not doc_text:
        raise ValueError("No text could be extracted from the PDF")

    agent = _build_agent(api_key)
    prompt = NER_PROMPT_TEMPLATE.format(text=doc_text)
    response = agent.run(prompt)
    parsed = response.content
    if not isinstance(parsed, FinancialEntities):
        raise RuntimeError("Model returned unexpected output type")

    entities = _financial_entities_to_api_entities(parsed)
    return PdfExtractionResult(entities=entities, evidence={})