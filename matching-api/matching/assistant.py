"""Core matching and comparison logic."""
import os
import json
from google import genai
from google.genai import types
from .chromadb import get_vectorstore

# LLM Configuration
DEFAULT_MODEL = "gemini-3-pro-preview"

# Schema for structured comparison output using genai types
COMPARISON_SCHEMA = types.Schema(
    type=types.Type.ARRAY,
    items=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "unit_id": types.Schema(type=types.Type.STRING),
            "lernziele_match": types.Schema(type=types.Type.INTEGER, description="0-100 percent"),
            "empfehlung": types.Schema(type=types.Type.STRING, enum=["vollständig", "teilweise", "keine"]),
            "begründung": types.Schema(type=types.Type.STRING, description="Markdown formatted analysis")
        },
        required=["unit_id", "lernziele_match", "empfehlung", "begründung"]
    )
)


class MatchingAssistant:
    """Assistant for module matching and comparison."""

    def __init__(self, vectorstore_path: str = "./data/vectorstore"):
        self.collection = get_vectorstore(vectorstore_path)
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        self.model = os.getenv("LLM_MODEL", DEFAULT_MODEL)

    def find_matching_units(self, external_module_text: str, limit: int = 5) -> list[dict]:
        """Find top matching internal units for an external module.

        Args:
            external_module_text: Description of the external module/course
            limit: Number of results to return

        Returns:
            List of matching units with metadata and similarity scores
        """
        results = self.collection.query(
            query_texts=[external_module_text],
            n_results=limit,
            include=["documents", "metadatas", "distances"]
        )

        matches = []
        for i, (doc, meta, dist) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )):
            # Convert distance to similarity (cosine distance: 0 = identical)
            similarity = 1 - dist

            matches.append({
                "rank": i + 1,
                "unit_id": meta.get("unit_id"),
                "unit_title": meta.get("unit_title"),
                "module_id": meta.get("module_id"),
                "module_title": meta.get("module_title"),
                "semester": meta.get("semester"),
                "sws": meta.get("sws"),
                "credits": meta.get("credits"),
                "workload": meta.get("workload"),
                "similarity": round(similarity, 3),
                "content_preview": doc[:500] + "..." if len(doc) > 500 else doc
            })

        return matches

    def _call_llm(self, prompt: str) -> str:
        """Call Gemini LLM and return text response."""
        response = self.client.models.generate_content(
            model=self.model,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_modalities=["TEXT"],
            ),
        )

        for part in response.candidates[0].content.parts:
            if part.text:
                return part.text
        return ""

    def parse_external_module(self, raw_text: str) -> dict:
        """Parse unstructured external module text into structured format.

        Args:
            raw_text: Raw text from external module description

        Returns:
            Structured module data
        """
        prompt = """Du extrahierst Metadaten aus akademischen Modulbeschreibungen.
Antworte NUR mit validem JSON nach diesem Schema:
{
  "title": "Modultitel",
  "credits": 6,
  "workload": "180 Stunden",
  "learning_goals": ["Lernziel 1", "Lernziel 2"],
  "assessment": "Klausur",
  "level": "Bachelor",
  "institution": "Universität XY"
}

Wenn Informationen fehlen, verwende null oder leere Listen.

Dokument:
""" + raw_text[:8000]

        try:
            content = self._call_llm(prompt)
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            return {
                "title": "Unbekannt",
                "credits": None,
                "workload": None,
                "learning_goals": [],
                "assessment": None,
                "level": None,
                "institution": None,
                "raw_text": raw_text[:2000],
                "parse_error": True
            }

    def compare_modules(self, external_module: dict, internal_unit_id: str) -> dict:
        """Compare external module with internal unit and generate recommendation.

        Args:
            external_module: Parsed external module data
            internal_unit_id: ID of internal unit to compare against

        Returns:
            Comparison result with recommendation
        """
        # Get internal unit data
        internal = self.collection.get(
            ids=[internal_unit_id],
            include=["documents", "metadatas"]
        )

        if not internal["ids"]:
            return {"error": f"Unit {internal_unit_id} not found"}

        internal_doc = internal["documents"][0]
        internal_meta = internal["metadatas"][0]

        # Format modules for comparison
        external_text = self._format_module_for_comparison(external_module, is_external=True)
        internal_text = f"""**Unit:** {internal_meta.get('unit_title')}
**Modul:** {internal_meta.get('module_title')}
**Credits:** {internal_meta.get('credits')}
**SWS:** {internal_meta.get('sws')}
**Workload:** {internal_meta.get('workload')}
**Prüfung:** {internal_meta.get('pruefungsleistung')}

**Inhalt:**
{internal_doc}"""

        prompt = """Prüfe ob externes Modul auf interne Unit anerkennbar ist.

Kriterien:
- Lernziele: ≥80% → vollständig, ≥50% → teilweise, <50% → keine
- Credits: Extern ≥ Intern OK, ~10% Diff OK, Intern >> Extern → max teilweise
- Niveau: Bachelor/Master sollten passen
- Arbeitsaufwand/Prüfungsform: nur wenn vergleichbar

Antworte KURZ und SACHLICH (max 150 Wörter):
1. Lernziele-Übereinstimmung (geschätzt %)
2. Credits-Vergleich (OK/Problem)
3. Wesentliche Defizite (Stichpunkte, max 3)
4. **Empfehlung: vollständig/teilweise/keine**

Keine Anrede, keine Tabellen, keine Floskeln.

## Externes Modul
""" + external_text + """

## Interne Unit
""" + internal_text

        try:
            content = self._call_llm(prompt)

            # Extract recommendation from Markdown response
            recommendation = "offen"
            if "**Vollständige Anerkennung**" in content or "Vollständige Anerkennung empfohlen" in content:
                recommendation = "vollständig"
            elif "**Teilweise Anerkennung**" in content or "Teilweise Anerkennung empfohlen" in content:
                recommendation = "teilweise"
            elif "**Keine Anerkennung**" in content or "Keine Anerkennung empfohlen" in content:
                recommendation = "keine"

            return {
                "recommendation": recommendation,
                "reasoning": content,  # Full Markdown response
                "internal_unit_id": internal_unit_id,
                "internal_unit_title": internal_meta.get("unit_title"),
                "internal_module_title": internal_meta.get("module_title"),
            }

        except Exception as e:
            return {
                "error": f"LLM call failed: {e}",
                "recommendation": "offen",
                "reasoning": "",
            }

    def compare_multiple(self, external_module: dict, unit_ids: list[str]) -> list[dict]:
        """Compare external module with multiple internal units in one LLM call.

        Args:
            external_module: Parsed external module data
            unit_ids: List of unit IDs to compare against

        Returns:
            List of comparison results, one per unit
        """
        # Get all internal units
        units_data = []
        for unit_id in unit_ids:
            internal = self.collection.get(
                ids=[unit_id],
                include=["documents", "metadatas"]
            )
            if internal["ids"]:
                units_data.append({
                    "unit_id": unit_id,
                    "doc": internal["documents"][0],
                    "meta": internal["metadatas"][0]
                })

        if not units_data:
            return []

        # Format external module
        external_text = self._format_module_for_comparison(external_module, is_external=True)

        # Format all internal units
        units_text = ""
        for i, u in enumerate(units_data, 1):
            units_text += f"""
### Unit {i}: {u['meta'].get('unit_title')} ({u['unit_id']})
Modul: {u['meta'].get('module_title')}
Credits: {u['meta'].get('credits')}
{u['doc'][:1500]}

"""

        prompt = f"""Prüfe Anerkennbarkeit: Externes Modul → {len(units_data)} interne Units.

WICHTIG: Genau {len(units_data)} Ergebnisse zurückgeben - für JEDE Unit.

Kriterien:
- Lernziele: ≥80% → vollständig, ≥50% → teilweise, <50% → keine
- Credits: extern ≥ intern = OK

Pro Unit ausgeben:
- lernziele_match: 0-100%
- empfehlung: vollständig/teilweise/keine
- begründung: Ausführliche Markdown-Analyse (8-15 Zeilen):

  **Lernziel-Abgleich:**
  Für jedes Lernziel der internen Unit: ✓ abgedeckt / ✗ nicht abgedeckt
  - [Unit-Lernziel 1]: ✓/✗ Erklärung
  - [Unit-Lernziel 2]: ✓/✗ Erklärung

  **Credits:** X extern vs. Y intern → OK/Problem

  **Defizite:** Konkret was fehlt (falls vorhanden)

  **Fazit:** 2-3 Sätze mit klarer Empfehlung und Begründung.

Sachlich, keine Floskeln, keine Tabellen.

## Externes Modul
{external_text}

## Interne Units
{units_text}
"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=COMPARISON_SCHEMA,
                ),
            )

            result_text = response.candidates[0].content.parts[0].text
            results = json.loads(result_text)

            # Enrich with metadata including unit details for side-by-side comparison
            data_by_id = {u['unit_id']: u for u in units_data}
            for r in results:
                unit_data = data_by_id.get(r['unit_id'], {})
                meta = unit_data.get('meta', {})
                r['unit_title'] = meta.get('unit_title', '')
                r['module_title'] = meta.get('module_title', '')
                r['unit_credits'] = meta.get('credits')
                r['unit_sws'] = meta.get('sws')
                r['unit_workload'] = meta.get('workload')
                r['unit_content'] = unit_data.get('doc', '')[:2000]  # First 2000 chars for display

            return results

        except Exception as e:
            return [{"error": str(e)}]

    def _format_module_for_comparison(self, module: dict, is_external: bool = True) -> str:
        """Format module data for LLM comparison."""
        prefix = "Externes Modul" if is_external else "Internes Modul"

        parts = [f"**{prefix}:** {module.get('title', 'Unbekannt')}"]

        if module.get("credits"):
            parts.append(f"**Credits:** {module['credits']}")
        if module.get("workload"):
            parts.append(f"**Workload:** {module['workload']}")
        if module.get("level"):
            parts.append(f"**Niveau:** {module['level']}")
        if module.get("assessment"):
            parts.append(f"**Prüfung:** {module['assessment']}")
        if module.get("institution"):
            parts.append(f"**Institution:** {module['institution']}")

        if module.get("learning_goals"):
            goals = module["learning_goals"]
            if isinstance(goals, list):
                goals_text = "\n".join(f"- {g}" for g in goals)
            else:
                goals_text = str(goals)
            parts.append(f"**Lernziele:**\n{goals_text}")

        if module.get("raw_text"):
            parts.append(f"**Beschreibung:**\n{module['raw_text'][:1500]}")

        return "\n".join(parts)
