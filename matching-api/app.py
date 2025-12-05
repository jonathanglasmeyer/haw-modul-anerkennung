"""FastAPI REST API for module matching."""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# API Key auth
API_KEY = os.environ.get("API_KEY")

from matching import MatchingAssistant, sync_from_airtable


# Pydantic models for request/response
class MatchRequest(BaseModel):
    text: str
    limit: int = 5

class ParseRequest(BaseModel):
    text: str

class CompareRequest(BaseModel):
    external_module: dict
    internal_unit_id: str

class MatchAndCompareRequest(BaseModel):
    text: str
    auto_compare: bool = False

class CompareMultipleRequest(BaseModel):
    external_module: dict
    unit_ids: list[str]


# Global assistant instance
_assistant: MatchingAssistant | None = None


def get_assistant() -> MatchingAssistant:
    global _assistant
    if _assistant is None:
        vectorstore_path = os.getenv("VECTORSTORE_PATH", "./data/vectorstore")
        _assistant = MatchingAssistant(vectorstore_path)
    return _assistant


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Optionally sync from Airtable on startup (only if SYNC_ON_STARTUP=1)."""
    if os.getenv("SYNC_ON_STARTUP", "0") == "1":
        sync_from_airtable()
    yield


app = FastAPI(
    title="Module Matching API",
    description="API for matching external modules against internal curriculum units",
    version="0.1.0",
    lifespan=lifespan
)


@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    """Verify API key for all endpoints except /health."""
    if request.url.path == "/health":
        return await call_next(request)

    # Skip auth if no API_KEY configured (local dev)
    if not API_KEY:
        return await call_next(request)

    key = request.headers.get("X-API-Key")
    if key != API_KEY:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    return await call_next(request)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/match")
async def match_units(request: MatchRequest):
    """Find matching internal units for an external module description."""
    assistant = get_assistant()
    matches = assistant.find_matching_units(request.text, limit=request.limit)
    return {"matches": matches}


@app.post("/parse")
async def parse_module(request: ParseRequest):
    """Parse external module text into structured format using LLM."""
    assistant = get_assistant()
    module = assistant.parse_external_module(request.text)
    return {"module": module}


@app.post("/compare")
async def compare_modules(request: CompareRequest):
    """Compare external module with internal unit and get recommendation."""
    assistant = get_assistant()
    result = assistant.compare_modules(
        request.external_module,
        request.internal_unit_id
    )
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return {"result": result}


@app.post("/compare-multiple")
async def compare_multiple(request: CompareMultipleRequest):
    """Compare external module with multiple internal units in one LLM call."""
    assistant = get_assistant()
    results = assistant.compare_multiple(
        request.external_module,
        request.unit_ids
    )
    if results and "error" in results[0]:
        raise HTTPException(status_code=500, detail=results[0]["error"])
    return {"results": results}


@app.post("/match-and-compare")
async def match_and_compare(request: MatchAndCompareRequest):
    """Full pipeline: parse, find matches, optionally compare with top match."""
    assistant = get_assistant()

    # Parse external module
    parsed = assistant.parse_external_module(request.text)

    # Find matches
    matches = assistant.find_matching_units(request.text, limit=5)

    result = {
        "parsed_module": parsed,
        "matches": matches
    }

    # Auto-compare with top match if requested
    if request.auto_compare and matches:
        top_match_id = matches[0]["unit_id"]
        comparison = assistant.compare_modules(parsed, top_match_id)
        result["comparison"] = comparison

    return result


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3008))
    uvicorn.run(app, host="0.0.0.0", port=port)
