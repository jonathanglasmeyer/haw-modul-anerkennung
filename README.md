# HAW Hamburg Modulanerkennung

Web-Anwendung für die Anerkennung externer Module an der HAW Hamburg.

## Architektur

- **Frontend**: Next.js (React) - Web-GUI für Studierende
- **Backend**: FastAPI + ChromaDB + Gemini - Matching & Vergleich
- **Daten**: Airtable (Stammdaten: Module, Units, Verantwortliche)

## Workflow

1. Externes Modul eingeben (Text/Beschreibung)
2. System findet passende interne Units (Vector-Search)
3. LLM vergleicht Lernziele, Credits, Niveau
4. PDF-Bescheid + Email-Vorlage generieren

## Setup

### Backend

```bash
cd matching-api
cp .env.example .env
# .env ausfüllen: GEMINI_API_KEY, AIRTABLE_API_KEY, AIRTABLE_BASE_ID
uv run --env-file .env python scripts/load_units.py  # Einmalig: Units laden
uv run --env-file .env python app.py  # Server starten (Port 3008)
```

### Frontend

```bash
cd frontend
cp .env.local.example .env.local
# .env.local ausfüllen: NEXT_PUBLIC_MATCHING_API_URL
npm install
npm run dev  # Dev-Server (Port 3000)
```

## Deployment

- **Backend**: Hetzner VPS (https://matching-api.quietloop.dev) - Auto-Deploy bei push auf `main`
- **Frontend**: Lokal (Development)

Siehe [.github/DEPLOYMENT.md](.github/DEPLOYMENT.md) für Auto-Deploy Setup.

## Technologien

- **Embeddings**: Gemini `gemini-embedding-001`
- **LLM**: Gemini `gemini-2.0-flash-thinking-exp-1219`
- **Vector-Store**: ChromaDB (lokal)
- **PDF**: reportlab
- **Frontend**: Next.js 15, Tailwind, shadcn/ui

## Lizenz

MIT
