from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from .docx_parser import extract_entities_from_docx_bytes
from .ner_pdf import extract_entities_from_pdf_bytes


def create_app() -> FastAPI:
    app = FastAPI(title="CMI NER Case Study", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/ner")
    async def ner(file: UploadFile = File(...)) -> JSONResponse:
        filename = (file.filename or "").strip().lower()
        if not filename:
            raise HTTPException(
                status_code=400,
                detail="A file with a supported extension (.docx or .pdf) is required.",
            )

        data = await file.read()

        if filename.endswith(".docx"):
            result = extract_entities_from_docx_bytes(data)
            return JSONResponse(result.to_json_dict())

        if filename.endswith(".pdf"):
            try:
                result = extract_entities_from_pdf_bytes(data)
            except ValueError as e:
                msg = str(e)
                if "TOGETHER_API_KEY" in msg:
                    raise HTTPException(status_code=503, detail=msg) from e
                raise HTTPException(status_code=400, detail=msg) from e
            except Exception as e:
                raise HTTPException(
                    status_code=502,
                    detail=f"NER request failed: {e}",
                ) from e
            return JSONResponse(result.to_json_dict())

        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Upload a .docx or .pdf file.",
        )

    return app
