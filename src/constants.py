# ── Model ─────────────────────────────────────────────────────────────────────
TOGETHER_MODEL_ID = "openai/gpt-oss-20b"

# ── Text extraction ───────────────────────────────────────────────────────────
DEFAULT_MAX_CHARS = 4_000
TOP_K = 5

# ── LLM sampling ─────────────────────────────────────────────────────────────
LLM_TEMPERATURE = 0.1
LLM_MAX_TOKENS = 500
LLM_TOP_P = 0.95

# ── Prompts ───────────────────────────────────────────────────────────────────
NER_PROMPT_TEMPLATE = """Extract financial entities from the following document text.
Return null for any field not found.

Document:
{text}"""