from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from .docx_parser import extract_entities_from_docx_bytes


def create_app() -> FastAPI:
    app = FastAPI(title="CMI NER Case Study", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/ner/docx")
    async def ner_docx(file: UploadFile = File(...)) -> JSONResponse:
        if not file.filename or not file.filename.lower().endswith(".docx"):
            raise HTTPException(status_code=400, detail="Please upload a .docx file.")
        data = await file.read()
        result = extract_entities_from_docx_bytes(data)
        return JSONResponse(result.to_json_dict())

    return app

