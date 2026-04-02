from __future__ import annotations

from enum import StrEnum


class FinancialEntity(StrEnum):
    counterparty = "Counterparty"
    initial_valuation_date = "Initial Valuation Date"
    notional = "Notional"
    valuation_date = "Valuation Date"
    maturity = "Maturity"
    underlying = "Underlying"
    coupon = "Coupon"
    barrier = "Barrier"
    calendar = "Calendar"


CANONICAL_ORDER: list[FinancialEntity] = [
    FinancialEntity.counterparty,
    FinancialEntity.initial_valuation_date,
    FinancialEntity.notional,
    FinancialEntity.valuation_date,
    FinancialEntity.maturity,
    FinancialEntity.underlying,
    FinancialEntity.coupon,
    FinancialEntity.barrier,
    FinancialEntity.calendar,
]

