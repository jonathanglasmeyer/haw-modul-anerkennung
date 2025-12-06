"""FastAPI REST API for module matching."""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from dotenv import load_dotenv
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.colors import HexColor

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

class ExportPDFRequest(BaseModel):
    external_module: dict
    results: list[dict]


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
    return assistant.find_matching_units(request.text, limit=request.limit)


@app.post("/parse")
async def parse_module(request: ParseRequest):
    """Parse external module text into structured format using LLM."""
    assistant = get_assistant()
    return assistant.parse_external_module(request.text)


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
    """Compare external module with multiple internal units using parallel calls."""
    assistant = get_assistant()
    result = assistant.compare_multiple(
        request.external_module,
        request.unit_ids
    )
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    if result.get("results") and len(result["results"]) > 0 and "error" in result["results"][0]:
        raise HTTPException(status_code=500, detail=result["results"][0]["error"])
    return result


@app.post("/match-and-compare")
async def match_and_compare(request: MatchAndCompareRequest):
    """Full pipeline: parse, find matches, optionally compare with top match."""
    assistant = get_assistant()

    # Parse external module
    parse_result = assistant.parse_external_module(request.text)

    # Find matches
    match_result = assistant.find_matching_units(request.text, limit=5)

    result = {
        "parsed_module": parse_result.get("module"),
        "matches": match_result.get("matches"),
        "timing": {
            **parse_result.get("timing", {}),
            **match_result.get("timing", {})
        }
    }

    # Auto-compare with top match if requested
    if request.auto_compare and match_result.get("matches"):
        top_match_id = match_result["matches"][0]["unit_id"]
        comparison = assistant.compare_modules(parse_result.get("module"), top_match_id)
        result["comparison"] = comparison

    return result


@app.post("/export-pdf")
async def export_pdf(request: ExportPDFRequest, req: Request):
    if API_KEY and req.headers.get("x-api-key") != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Generate PDF
    pdf_bytes = generate_pdf(request.external_module, request.results)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=anerkennungsantrag.pdf"}
    )


def generate_pdf(external_module: dict, results: list[dict]) -> bytes:
    """Generate PDF using reportlab"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)

    story = []
    styles = getSampleStyleSheet()

    # Custom styles - NO ITALIC!
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Normal'],
        fontSize=20,
        fontName='Helvetica-Bold',
        textColor=HexColor('#1a1a1a'),
        spaceAfter=12
    )

    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=HexColor('#6b7280'),
        spaceAfter=20
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Normal'],
        fontSize=16,
        fontName='Helvetica-Bold',
        textColor=HexColor('#374151'),
        spaceBefore=20,
        spaceAfter=12
    )

    unit_title_style = ParagraphStyle(
        'UnitTitle',
        parent=styles['Normal'],
        fontSize=14,
        fontName='Helvetica-Bold',
        textColor=HexColor('#1a1a1a'),
        spaceBefore=10,
        spaceAfter=6,
        leading=18
    )

    detail_heading_style = ParagraphStyle(
        'DetailHeading',
        parent=styles['Normal'],
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=HexColor('#1a1a1a'),
        spaceBefore=4,
        spaceAfter=2
    )

    # Title
    story.append(Paragraph("Anerkennungsantrag", title_style))
    story.append(Paragraph("HAW Hamburg - Anerkennung externer Module", subtitle_style))

    # External Module
    story.append(Paragraph("Externes Modul", heading_style))
    story.append(Spacer(1, 0.3*cm))

    mod_title = f"<b>{external_module.get('title', 'N/A')}</b>"
    story.append(Paragraph(mod_title, styles['Normal']))
    story.append(Spacer(1, 0.2*cm))

    # Add module details
    details = []
    if external_module.get('credits'):
        details.append(f"Credits: {external_module['credits']}")
    if external_module.get('workload'):
        details.append(f"Workload: {external_module['workload']}")
    if external_module.get('level'):
        details.append(f"Niveau: {external_module['level']}")
    if external_module.get('assessment'):
        details.append(f"Prüfung: {external_module['assessment']}")
    if external_module.get('institution'):
        details.append(f"Institution: {external_module['institution']}")

    if details:
        story.append(Paragraph(" | ".join(details), styles['Normal']))
        story.append(Spacer(1, 0.3*cm))

    # Learning goals
    if external_module.get('learning_goals'):
        story.append(Paragraph("<b>Lernziele:</b>", styles['Normal']))
        story.append(Spacer(1, 0.1*cm))
        for goal in external_module['learning_goals']:
            story.append(Paragraph(f"• {goal}", styles['Normal']))
        story.append(Spacer(1, 0.3*cm))

    # Internal modules
    story.append(Paragraph("Interne Module - Assessment", heading_style))

    for idx, result in enumerate(results, 1):
        story.append(Spacer(1, 0.5*cm))

        unit_title = f"<b>{idx}. {result.get('unit_title', 'N/A')}</b>"
        story.append(Paragraph(unit_title, unit_title_style))

        if result.get('module_title'):
            story.append(Paragraph(f"Modul: {result['module_title']}", styles['Normal']))

        story.append(Spacer(1, 0.2*cm))

        # Empfehlung
        empf = result.get('empfehlung', '')
        empf_text = "Vollständige Anerkennung" if empf == "vollständig" else "Teilweise Anerkennung" if empf == "teilweise" else "Keine Anerkennung"
        story.append(Paragraph(f"<b>Empfehlung: {empf_text}</b>", styles['Normal']))

        story.append(Spacer(1, 0.1*cm))

        # Metadaten Grid
        meta_parts = [f"<b>Lernziele Match:</b> {result.get('lernziele_match', 'N/A')}%"]
        if result.get('unit_credits') is not None:
            meta_parts.append(f"<b>Credits (intern):</b> {result['unit_credits']}")
        if result.get('unit_sws') is not None:
            meta_parts.append(f"<b>SWS:</b> {result['unit_sws']}")
        if result.get('unit_workload'):
            meta_parts.append(f"<b>Workload:</b> {result['unit_workload']}")
        if result.get('verantwortliche'):
            meta_parts.append(f"<b>Verantwortliche:</b> {result['verantwortliche']}")

        story.append(Paragraph(" | ".join(meta_parts), styles['Normal']))
        story.append(Spacer(1, 0.3*cm))

        # Details-Sektion (wie im Frontend)

        # Lernziel-Abgleich
        if result.get('lernziele') and len(result['lernziele']) > 0:
            story.append(Paragraph("Lernziel-Abgleich", detail_heading_style))
            story.append(Spacer(1, 0.1*cm))
            for lz in result['lernziele']:
                status = lz.get('status', 'N/A')
                ziel = lz.get('ziel', 'N/A')
                note = lz.get('note', '')
                lz_text = f"<b>{status}</b> <b>{ziel}:</b> {note}"
                story.append(Paragraph(lz_text, styles['Normal']))
            story.append(Spacer(1, 0.2*cm))

        # Credits (mit Vergleich)
        if result.get('credits'):
            extern = result['credits'].get('extern', 'n/a')
            intern = result['credits'].get('intern', 'n/a')
            bewertung = result['credits'].get('bewertung', '')
            story.append(Paragraph("Credits", detail_heading_style))
            story.append(Paragraph(f"Extern: {extern} | Intern: {intern} — {bewertung}", styles['Normal']))
            story.append(Spacer(1, 0.2*cm))

        # Niveau
        if result.get('niveau'):
            story.append(Paragraph("Niveau", detail_heading_style))
            story.append(Paragraph(result['niveau'], styles['Normal']))
            story.append(Spacer(1, 0.2*cm))

        # Prüfung
        if result.get('pruefung'):
            story.append(Paragraph("Prüfung", detail_heading_style))
            story.append(Paragraph(result['pruefung'], styles['Normal']))
            story.append(Spacer(1, 0.2*cm))

        # Workload (Vergleich)
        if result.get('workload'):
            story.append(Paragraph("Workload", detail_heading_style))
            story.append(Paragraph(result['workload'], styles['Normal']))
            story.append(Spacer(1, 0.2*cm))

        # Defizite
        if result.get('defizite') and len(result['defizite']) > 0:
            story.append(Paragraph("Defizite", detail_heading_style))
            for defizit in result['defizite']:
                story.append(Paragraph(f"• {defizit}", styles['Normal']))
            story.append(Spacer(1, 0.2*cm))

        # Fazit
        if result.get('fazit'):
            story.append(Paragraph("Fazit", detail_heading_style))
            story.append(Paragraph(result['fazit'], styles['Normal']))

    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.read()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3008))
    uvicorn.run(app, host="0.0.0.0", port=port)
