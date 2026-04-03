# CMI NER — Financial Entity Extraction

A FastAPI service that extracts structured financial entities from `.docx`, `.pdf`, and `.txt` files using a hybrid pipeline: rule-based extraction for Word documents and LLM-based NER (via [Together AI](https://www.together.ai/) + [Agno](https://docs.agno.com/)) for PDFs and plain text.

---

## Architecture
```
.
├── api.py             # FastAPI app and /ner endpoint
├── entities.py        # Shared Pydantic schema (FinancialEntities)
├── constants.py       # Shared LLM and extraction constants
├── docx_constants.py  # Regex patterns and rules for docx extraction
├── docx_parser.py     # Rule-based entity extractor for .docx files
├── ner_pdf.py         # LLM-based NER for .pdf files (pdfplumber + Agno)
└── ner_chat.py        # LLM-based NER for .txt files + fine-tuning utilities
```

### Extraction strategies by file type

| File type | Strategy | Model |
|-----------|-----------|-------|
| `.docx`   | Rule-based (regex + key-value heuristics) | — |
| `.pdf`    | LLM NER via Together AI | `openai/gpt-oss-20b` |
| `.txt`    | LLM NER via Together AI | `openai/gpt-oss-20b` |

---

## Extracted Entities

All three pipelines return the same JSON shape defined in `entities.py`:

| Field | Description |
|-------|-------------|
| `Counterparty` | The other party in the agreement |
| `InitialValuationDate` | First pricing or initial valuation date |
| `ValuationDate` | Valuation date (non-initial) |
| `Maturity` | Date or term, e.g. `2Y`, `2025-12-31` |
| `Notional` | Amount including currency, e.g. `200 mio USD` |
| `Underlying` | Reference asset or index |
| `Coupon` | Interest rate, e.g. `3.5%` |
| `Barrier` | Trigger level if specified |
| `Calendar` | Holiday calendar used |

---

## Setup

### 1. Clone and install
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# then set your key:
TOGETHER_API_KEY=your_key_here
```

### 3. Run the API
```bash
uvicorn cmi_ner.api:create_app --factory --reload
```

The service starts on `http://localhost:8000`.

---

## API

### `GET /health`
```json
{ "status": "ok" }
```

### `POST /ner`

Upload a file for entity extraction.

**Request** — `multipart/form-data`

| Field | Type | Description |
|-------|------|-------------|
| `file` | file | `.docx`, `.pdf`, or `.txt` |

**Response** `200 OK`
```json
{
  "entities": {
    "Counterparty": "BANK ABC",
    "Notional": "200 mio USD",
    "Maturity": "2Y",
    "Underlying": "FR001400QV82",
    "Coupon": "",
    "Barrier": "",
    "InitialValuationDate": "",
    "ValuationDate": "",
    "Calendar": ""
  },
  "evidence": {
    "Counterparty": ["Counterparty: BANK ABC"]
  }
}
```

> `evidence` is populated for `.docx` (the matched source line). It is always `{}` for PDF and TXT responses.

**Error codes**

| Code | Reason |
|------|--------|
| `400` | Missing file, unsupported extension, or empty/unreadable content |
| `503` | `TOGETHER_API_KEY` not set |
| `502` | Upstream LLM call failed |

**Example with curl**
```bash
curl -X POST http://localhost:8000/ner \
  -F "file=@term_sheet.pdf"
```

---

## Fine-tuning (optional)

`ner_chat.py` includes utilities to generate synthetic training data and submit a LoRA fine-tuning job to Together AI:
```bash
# Generate synthetic JSONL dataset
python -m src.ner_chat  # runs main() by default
```

Once the job completes, set `FINE_TUNED_MODEL_ID` in `ner_chat.py` to the returned model ID to use the fine-tuned weights.

---

## Configuration

All tuneable constants live in `constants.py` and `docx_constants.py` — no magic numbers in module logic.

| Constant | Default | Description |
|----------|---------|-------------|
| `TOGETHER_MODEL_ID` | `openai/gpt-oss-20b` | Together AI model used for NER |
| `DEFAULT_MAX_CHARS` | `4 000` | Max characters sent to the LLM |
| `TOP_K` | `5` | Top chunks retrieved (RAG path) |
| `LLM_TEMPERATURE` | `0.1` | Sampling temperature |
| `LLM_MAX_TOKENS` | `500` | Max tokens in LLM response |
| `LLM_TOP_P` | `0.95` | Nucleus sampling parameter |