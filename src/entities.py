from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class FinancialEntities(BaseModel):
    """Shared schema for financial NER (LLM structured output and docx extraction)."""

    model_config = ConfigDict(populate_by_name=True)

    Counterparty: Optional[str] = Field(None, description="The other party in the agreement")
    InitialValuationDate: Optional[str] = Field(
        None,
        description="First pricing or initial valuation date",
    )
    Notional: Optional[str] = Field(
        None, description="Amount including currency, e.g. 200 mio USD"
    )
    ValuationDate: Optional[str] = Field(
        None,
        description="Valuation date (non-initial)",
    )
    Maturity: Optional[str] = Field(
        None, description="Date or term, e.g. 2Y, 2025-12-31"
    )
    Underlying: Optional[str] = Field(
        None, description="Reference asset or index"
    )
    Coupon: Optional[str] = Field(
        None, description="Interest rate, e.g. 3.5%"
    )
    Barrier: Optional[str] = Field(
        None, description="Trigger level if specified"
    )
    Calendar: Optional[str] = Field(
        None, description="Holiday calendar used"
    )
