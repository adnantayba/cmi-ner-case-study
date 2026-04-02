# cmi-ner-case-study

PoC for **Named Entity Recognition (NER)** tailored for financial documents (term sheets, confirmations, chat logs).

This repo is built step-by-step. **Step 1 (this version)** covers the **DOCX rule-based parser** only.

## Entities (DOCX)

- Counterparty
- Initial Valuation Date
- Notional
- Valuation Date
- Maturity
- Underlying
- Coupon
- Barrier
- Calendar

## Setup

```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

## Run (API)

```bash
uvicorn src.api:create_app --factory --reload
```

Then `POST /ner/docx` with a `.docx` file upload.
