import io
import logging
import os
from pathlib import Path
from typing import Any

import pdfplumber
from agno.agent import Agent
from agno.models.together import Together
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict

from .constants import (
    DEFAULT_MAX_CHARS,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    LLM_TOP_P,
    NER_PROMPT_TEMPLATE,
    TOGETHER_MODEL_ID,
)
from .entities import FinancialEntities

load_dotenv()

logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")


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


def financial_entities_to_extraction_result(fe: FinancialEntities) -> PdfExtractionResult:
    """Shared wrapper for LLM NER responses (documents, chat logs, plain text)."""
    return PdfExtractionResult(entities=_financial_entities_to_api_entities(fe), evidence={})


def _build_agent(api_key: str) -> Agent:
    return Agent(
        model=Together(
            id=TOGETHER_MODEL_ID,
            api_key=api_key,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
            top_p=LLM_TOP_P,
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
    """Run PDF text extraction and Together/Agno NER. Raises ValueError for config/input issues."""
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

    return financial_entities_to_extraction_result(parsed)