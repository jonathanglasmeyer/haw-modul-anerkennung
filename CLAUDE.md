# Projekt: Anerkennungsbescheide-Assistenz für Stephan

## Kontext
Wissenschaftlicher Mitarbeiter an Hochschule, bearbeitet ~75 Anerkennungsanträge/Semester. Studis wollen Prüfungsleistungen aus anderen Studiengängen anerkennen lassen.

**Wichtig:** Anerkennung erfolgt auf **Unit-Ebene**, nicht Modul-Ebene.

## Architektur

### Studi-Flow (Web-GUI)
1. Studi gibt externes Modul ein (Text/PDF)
2. System zeigt passende interne Units (Vector-Search + LLM-Vergleich)
3. Studi wählt Match → bekommt fertigen Email-Content für Stephan

### Stephan-Flow (Email-Automation)
1. Strukturierte Email von Studi (Unit-Match + Begründung)
2. Email-Automation → automatisch an zuständigen Prof weiterleiten
3. Prof antwortet ja/nein → Bescheid

### Datenbank: NeonDB (Serverless Postgres)
- **Personen**: Profs/Verantwortliche (16 entries)
- **Module**: Modul-Metadaten (30 entries)
- **Units**: Unit-Ebene mit Verantwortlichen-Zuordnung (72 entries)
- → Routing-Lookup: Unit-ID → zuständiger Prof
- **Migration**: `scripts/migrate_airtable_to_neondb.py` (Airtable→NeonDB one-time import)
- **Admin API**: `/api/admin/*` endpoints für CRUD (Session-Auth via ADMIN_PASSWORD)

## Matching-API (`matching-api/`)

FastAPI + ChromaDB + Gemini. Auth via `X-API-Key` header.

**Embedding-Architektur:**
- ChromaDB: lokaler Vektor-Speicher + Suche (persistent volume)
- Gemini Embedding API (`gemini-embedding-001`): Text→Vektor
- Sync: NeonDB Units → Gemini (einmalig ~72 calls) → ChromaDB
- Match-Request: Query→Gemini (1 call) → ChromaDB-Suche (lokal)
- Keine lokalen ML-Libs (kein torch/scipy) → Docker ~100MB, Build ~5s

**Endpoints:**
- `GET /health` - Health check (public)
- `POST /match` - Vector-Search für Top-N Units
- `POST /parse` - Externes Modul → strukturiertes JSON
- `POST /compare-multiple` - Parallele Single-Calls (ThreadPoolExecutor); jede Unit unabhängig bewertet

**Vergleichskriterien:** Lernziele (≥80%→vollständig, ≥50%→teilweise, <50%→keine); Credits extern≥intern OK; Bachelor/Master muss passen.

**LLM:** `gemini-flash-latest` (Gemini 2.5 Flash); ~6s für 2-Unit-Vergleich parallel.

**Deployment:** Hetzner VPS auto-deploy via GitHub Actions on push to `main`. URL: `https://matching-api.quietloop.dev`. Port 3008. Env: `DATABASE_URL` (NeonDB unpooled), `ADMIN_PASSWORD`, `GEMINI_API_KEY`, `SYNC_ON_STARTUP=1`, `CHROMADB_PERSISTENT=1`

**Local Dev:**
- Port 3008 (default; override via `PORT` env var)
- `uv run --env-file .env python app.py` (doesn't auto-load envs)
- ChromaDB: `CHROMADB_PERSISTENT=1` required (else in-memory, data lost)
- CORS allows `localhost:3007` (frontend dev)

## Frontend (`../frontend/`)

Next.js 15 + shadcn/ui deployed auf Vercel.

**Tech Stack:**
- Next.js 15.1 (App Router) + React 18
- shadcn/ui (Radix UI primitives) + Tailwind CSS v4
- Vercel Hosting

**3-Step Workflow:**
1. Input → Module eingeben (Textarea/PDF)
2. Matches → Top 10 Units auswählen (Checkbox-Liste)
3. Results → Vergleichsergebnisse + Email/PDF Export

**API Integration:**
- Proxy-Routes: `/api/{parse,match,compare-multiple}` → matching-api via X-API-Key
- `lib/matching-service.ts` - Matching API client
- `lib/admin-service.ts` - Admin API client (session auth)

**Admin UI (`/admin`):**
- Password auth (ADMIN_PASSWORD); session tokens in sessionStorage
- CRUD for Units/Module/Personen: `app/admin/{units,modules,personen}/page.tsx`
- ChromaDB sync button: triggers backend `/api/admin/sync`

**Local Dev:**
- Port 3007 (all npm scripts: `dev`, `dev:local`, `dev:prod`)
- `npm run dev:local` - Points to localhost:3008 (overrides NEXT_PUBLIC_MATCHING_API_URL)
- `npm run dev:prod` - Points to production API (explicit)

## Datenquellen

**Kern (`data/kern/`):**
- `modulhandbuecher/*.pdf` - Modulhandbuch-PDFs
- `uebersichten/Übersicht Units.xlsx` - Unit-Liste mit Verantwortlichen
- `vorlagen/bescheid-vorlage.docx` - Word-Template

**ChromaDB:** Vector-Store für semantic search (`./data/vectorstore/`)

## Scripts

- `scripts/load_units.py` - Units aus NeonDB in ChromaDB syncen
- `scripts/migrate_airtable_to_neondb.py` - Einmalige Migration Airtable→NeonDB

## Referenzen
- TH Lübeck Prototyp: https://github.com/pascalhuerten/recog-ai-demo
