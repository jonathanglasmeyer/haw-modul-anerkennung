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

### Airtable (nur Stammdaten, kein GDPR-Risiko)
- **Personen**: Profs/Verantwortliche
- **Module**: Modul-Metadaten
- **Units**: Unit-Ebene mit Verantwortlichen-Zuordnung
- → Routing-Lookup: Unit-ID → zuständiger Prof

## Matching-API (`matching-api/`)

FastAPI + ChromaDB + Gemini. Auth via `X-API-Key` header.

**Embedding-Architektur:**
- ChromaDB: lokaler Vektor-Speicher + Suche (persistent volume)
- Gemini Embedding API (`gemini-embedding-001`): Text→Vektor
- Sync: Airtable Units → Gemini (einmalig ~72 calls) → ChromaDB
- Match-Request: Query→Gemini (1 call) → ChromaDB-Suche (lokal)
- Keine lokalen ML-Libs (kein torch/scipy) → Docker ~100MB, Build ~5s

**Endpoints:**
- `GET /health` - Health check (public)
- `POST /match` - Vector-Search für Top-N Units
- `POST /parse` - Externes Modul → strukturiertes JSON
- `POST /compare-multiple` - Parallele Single-Calls (ThreadPoolExecutor); jede Unit unabhängig bewertet

**Vergleichskriterien:** Lernziele (≥80%→vollständig, ≥50%→teilweise, <50%→keine); Credits extern≥intern OK; Bachelor/Master muss passen.

**Performance:** `thinking_budget=1000` (nicht dynamic=default); ~6s für 2-Unit-Vergleich parallel.

**Deployment:** Hetzner VPS via `./deploy.sh`. URL: `https://matching-api.quietloop.dev`. Port 3008. Env: `GEMINI_API_KEY`, `AIRTABLE_API_KEY`, `SYNC_ON_STARTUP=1`

**Local Development:**
- `uv run` requires `--env-file .env` flag (doesn't auto-load like python-dotenv)
- ChromaDB needs `CHROMADB_PERSISTENT=1` in .env; otherwise in-memory (data lost)
- Commands: `uv run --env-file .env python app.py`, `uv run --env-file .env python scripts/load_units.py --force`
- Gemini caching not viable (units ~576 tokens < 2048 minimum)

## Frontend (geplant)

Next.js auf Cloudflare Workers. API Route ruft Matching-API mit X-API-Key. Secrets via `wrangler secret put MATCHING_API_KEY`.

Pattern aus `picnic-api-integration/web-ui/src/app/api/categories/route.ts`:
```typescript
fetch(process.env.MATCHING_API_URL + '/match', {
  headers: { 'X-API-Key': process.env.MATCHING_API_KEY }
})
```

## Datenquellen

**Kern (`data/kern/`):**
- `modulhandbuecher/*.pdf` - Modulhandbuch-PDFs
- `uebersichten/Übersicht Units.xlsx` - Unit-Liste mit Verantwortlichen
- `vorlagen/bescheid-vorlage.docx` - Word-Template

**ChromaDB:** Vector-Store für semantic search (`./data/vectorstore/`)

## Airtable

**Base:** Siehe `.env` für Base ID

| Tabelle | Zweck |
|---------|-------|
| Personen | Profs/Verantwortliche |
| Module | Modul-Metadaten |
| Units | Unit-Ebene + Verantwortliche |

**Zugriff:** `source .env && AIRTABLE_API_KEY="$AIRTABLE_API_KEY" mcporter airtable.<tool>`

## Scripts

- `scripts/load_units.py` - Units aus Airtable in ChromaDB laden

## Referenzen
- TH Lübeck Prototyp: https://github.com/pascalhuerten/recog-ai-demo
