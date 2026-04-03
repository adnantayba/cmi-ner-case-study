from __future__ import annotations

import json
import os
from pathlib import Path

import together
from agno.agent import Agent
from agno.models.together import Together
from dotenv import load_dotenv

from .entities import FinancialEntities
from .ner_pdf import (
    PdfExtractionResult,
    financial_entities_to_extraction_result,
)
from .constants import (
    DEFAULT_MAX_CHARS,
    LLM_MAX_TOKENS,
    LLM_TOP_P,
    NER_PROMPT_TEMPLATE,
    TOGETHER_MODEL_ID
)
load_dotenv()
together_api_key = os.getenv("TOGETHER_API_KEY")
BASE_MODEL = TOGETHER_MODEL_ID


def extract_text_from_txt_bytes(data: bytes, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    """Decode plain text from upload bytes (truncated to max_chars)."""
    text = data.decode("utf-8", errors="replace").strip()
    if len(text) > max_chars:
        text = text[:max_chars]
    return text.strip()


def _build_txt_ner_agent(api_key: str, model_id: str) -> Agent:
    return Agent(
        model=Together(
            id=model_id,
            api_key=api_key,
            temperature=0.8,
            max_tokens=LLM_MAX_TOKENS,
            top_p=LLM_TOP_P,
        ),
        description="Financial chat and text analyzer for entity extraction",
        output_schema=FinancialEntities,
        use_json_mode=True,
    )


def extract_entities_from_txt_bytes(
    data: bytes,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    model_id: str | None = None,
) -> PdfExtractionResult:
    """
    UTF-8 text + Together/Agno NER. Same JSON shape as PDF NER and docx API.
    Raises ValueError for missing API key or empty text.
    """
    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key:
        raise ValueError("TOGETHER_API_KEY is not set")

    mid = model_id or TOGETHER_MODEL_ID
    text = extract_text_from_txt_bytes(data, max_chars=max_chars)
    if not text:
        raise ValueError("No text content in the file")

    agent = _build_txt_ner_agent(api_key, mid)
    prompt = NER_PROMPT_TEMPLATE.format(text=text)
    response = agent.run(prompt)
    parsed = response.content
    if not isinstance(parsed, FinancialEntities):
        raise RuntimeError("Model returned unexpected output type")
    return financial_entities_to_extraction_result(parsed)


def run_ner_on_txt(txt_path: str, model_id: str) -> PdfExtractionResult:
    """Run NER on a plain-text file path (CLI / scripts)."""
    path = Path(txt_path)
    if not path.is_file():
        raise FileNotFoundError(f"Text file not found: {txt_path}")
    return extract_entities_from_txt_bytes(path.read_bytes(), model_id=model_id)


# --- Synthetic data generation ---


def generate_synthetic_dataset(output_path: str, count: int = 10) -> None:
    """
    Uses the LLM to generate synthetic chat/text logs and their labels
    based on the provided mission data [cite: 110-124].
    """
    generator = Agent(
        model=Together(id=BASE_MODEL, api_key=together_api_key),
        instructions=[
            "You are a data generator for financial NER.",
            "Generate short chat messages or text fragments between traders.",
            "Include entities: Counterparty, Notional, ISIN, Underlying, Maturity, Coupon, and Barrier.",
            "Format each line as a JSON object with 'text' and 'labels' keys for Together AI finetuning.",
        ],
    )

    seed_examples = [
        "I'll revert regarding BANK ABC to try to do another 200 mio at 2Y FR001400QV82",
        "AVMAFC FLOAT offer 2Y EVG estr+45bps 06/30/28",
        "Counterparty: BANK ABC, Notional: 200 mio, ISIN: FR001400QV82",
    ]

    with open(output_path, "w", encoding="utf-8") as f:
        for _i in range(count):
            prompt = f"Generate a unique financial chat log variation based on these: {seed_examples}"
            response = generator.run(prompt)
            f.write(json.dumps({"text": response.content, "label": "..."}) + "\n")

    print(f"Dataset generated: {output_path}")


def run_finetuning(file_path: str) -> str:
    """Submits the synthetic data to Together AI for LoRA fine-tuning[cite: 100]."""
    upload_resp = together.Files.upload(file=file_path)
    file_id = upload_resp["id"]

    job = together.Finetune.create(
        training_file=file_id,
        model=BASE_MODEL,
        n_epochs=3,
        batch_size=4,
        learning_rate=1e-5,
        suffix="fin-ner-poc",
    )

    job_id = job["id"]
    print(f"Fine-tuning started. Job ID: {job_id}")
    return job_id


def main() -> None:
    dataset_file = "synthetic_train.jsonl"
    target_txt = "chat_log.txt"

    FINE_TUNED_MODEL_ID = "openai/gpt-oss-20b"

    if not os.path.exists(target_txt):
        print(f"Creating sample {target_txt}...")
        with open(target_txt, "w", encoding="utf-8") as f:
            f.write(
                "11:49:05 I'll revert regarding BANK ABC to try to do another 200 mio at 2Y FR001400QV82\n"
            )
            f.write("AVMAFC FLOAT offer 2Y EVG estr+45bps 06/30/28\n")

    if not os.path.exists(dataset_file) or os.path.getsize(dataset_file) == 0:
        print("No dataset found. Generating synthetic data...")
        generate_synthetic_dataset(dataset_file)
    else:
        print(f"Using existing dataset: {dataset_file}")

    if FINE_TUNED_MODEL_ID == BASE_MODEL:
        print(
            "Notice: You are using the BASE_MODEL. Update FINE_TUNED_MODEL_ID to skip training in the future."
        )
    else:
        print(f"Using fine-tuned model: {FINE_TUNED_MODEL_ID}")

    print(f"Running NER on {target_txt} using {FINE_TUNED_MODEL_ID}...")
    result = run_ner_on_txt(target_txt, FINE_TUNED_MODEL_ID)

    print("Extracted Entities:")
    print(json.dumps(result.to_json_dict(), indent=2))


if __name__ == "__main__":
    main()
