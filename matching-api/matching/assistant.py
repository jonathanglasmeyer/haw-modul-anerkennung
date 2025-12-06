"""Core matching and comparison logic."""
import os
import json
import time
import logging
from google import genai
from google.genai import types
from .chromadb import get_vectorstore

logger = logging.getLogger(__name__)

# LLM Configuration
DEFAULT_MODEL = "gemini-flash-latest"

# Schema for structured comparison output using genai types
COMPARISON_SCHEMA = types.Schema(
    type=types.Type.ARRAY,
    items=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "unit_id": types.Schema(type=types.Type.STRING),
            "lernziele_match": types.Schema(type=types.Type.INTEGER, description="0-100 percent"),
            "empfehlung": types.Schema(type=types.Type.STRING, enum=["vollständig", "teilweise", "keine"]),
            "lernziele": types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "ziel": types.Schema(type=types.Type.STRING),
                        "status": types.Schema(type=types.Type.STRING, description="✓|~|✗"),
                        "note": types.Schema(type=types.Type.STRING),
                    },
                    required=["ziel", "status", "note"]
                )
            ),
            "credits": types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "extern": types.Schema(type=types.Type.NUMBER, nullable=True),
                    "intern": types.Schema(type=types.Type.NUMBER, nullable=True),
                    "bewertung": types.Schema(type=types.Type.STRING),
                },
                required=["bewertung"]
            ),
            "niveau": types.Schema(type=types.Type.STRING),
            "pruefung": types.Schema(type=types.Type.STRING),
            "workload": types.Schema(type=types.Type.STRING),
            "defizite": types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(type=types.Type.STRING)
            ),
            "fazit": types.Schema(type=types.Type.STRING),
        },
        required=["unit_id", "lernziele_match", "empfehlung", "lernziele", "credits", "niveau", "pruefung", "workload", "defizite", "fazit"]
    )
)

SINGLE_COMPARISON_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "lernziele_match": types.Schema(type=types.Type.INTEGER, description="0-100 percent"),
        "empfehlung": types.Schema(type=types.Type.STRING, enum=["vollständig", "teilweise", "keine"]),
        "lernziele": COMPARISON_SCHEMA.items.properties["lernziele"],
        "credits": COMPARISON_SCHEMA.items.properties["credits"],
        "niveau": types.Schema(type=types.Type.STRING),
        "pruefung": types.Schema(type=types.Type.STRING),
        "workload": types.Schema(type=types.Type.STRING),
        "defizite": COMPARISON_SCHEMA.items.properties["defizite"],
        "fazit": types.Schema(type=types.Type.STRING),
    },
    required=["lernziele_match", "empfehlung", "lernziele", "credits", "niveau", "pruefung", "workload", "defizite", "fazit"]
)


class MatchingAssistant:
    """Assistant for module matching and comparison."""

    def __init__(self, vectorstore_path: str = "./data/vectorstore"):
        self.collection = get_vectorstore(vectorstore_path)
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        self.model = os.getenv("LLM_MODEL", DEFAULT_MODEL)

    def find_matching_units(self, external_module_text: str, limit: int = 5) -> dict:
        """Find top matching internal units for an external module.

        Args:
            external_module_text: Description of the external module/course
            limit: Number of results to return

        Returns:
            Dict with matches list and timing metadata
        """
        start = time.time()
        results = self.collection.query(
            query_texts=[external_module_text],
            n_results=limit,
            include=["documents", "metadatas", "distances"]
        )
        query_time = time.time() - start

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

        logger.info(f"Vector search completed in {query_time:.3f}s (embedding + query)")
        return {
            "matches": matches,
            "timing": {
                "vector_search_ms": round(query_time * 1000, 1)
            }
        }

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
            Dict with module data and timing metadata
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
            start = time.time()
            content = self._call_llm(prompt)
            llm_time = time.time() - start

            # Extract JSON from response (handle markdown code blocks)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            module_data = json.loads(content.strip())
            logger.info(f"Parse LLM call completed in {llm_time:.3f}s")

            return {
                "module": module_data,
                "timing": {
                    "parse_llm_ms": round(llm_time * 1000, 1)
                }
            }
        except (json.JSONDecodeError, IndexError):
            return {
                "module": {
                    "title": "Unbekannt",
                    "credits": None,
                    "workload": None,
                    "learning_goals": [],
                    "assessment": None,
                    "level": None,
                    "institution": None,
                    "raw_text": raw_text[:2000],
                    "parse_error": True
                },
                "timing": {}
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

        prompt = """Prüfe, ob externes Modul auf interne Unit anerkennbar ist. Liefere JSON nach Schema:
{
  "lernziele_match": 0-100,
  "empfehlung": "vollständig"|"teilweise"|"keine",
  "lernziele": [
    {"ziel": "Unit-Ziel", "status": "✓|~|✗", "note": "1 Satz warum"}
  ],
  "credits": {"extern": Zahl|null, "intern": Zahl|null, "bewertung": "OK/Problem + 1 Satz"},
  "niveau": "Bachelor/Master Bewertung, 1 Satz",
  "pruefung": "Prüfungsform-Vergleich, 1 Satz",
  "workload": "Workload-Einordnung, 1 Satz",
  "defizite": ["konkrete Lücke 1", "…"],
  "fazit": "2-3 Sätze, klare Begründung + Empfehlung"
}

Kriterien:
- Lernziele: ≥80% → vollständig, ≥50% → teilweise, <50% → keine
- Credits: Extern ≥ Intern OK, bis ~10% Diff tolerierbar
- Niveau/Prüfung/Workload nur erwähnen wenn relevant
- Max 3 Defizite, sachlich, keine Floskeln.

## Externes Modul
""" + external_text + """

## Interne Unit
""" + internal_text

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=SINGLE_COMPARISON_SCHEMA,
                    thinking_config=types.ThinkingConfig(thinking_budget=-1),
                ),
            )

            content = response.candidates[0].content.parts[0].text
            parsed = json.loads(content)
            recommendation = parsed.get("empfehlung", "offen")
            return {
                "recommendation": recommendation,
                "reasoning": parsed.get("begründung", ""),
                "learning_goals_match": parsed.get("lernziele_match"),
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

WICHTIG: Gib GENAU {len(units_data)} Ergebnisse zurück (eins pro Unit) im JSON-Schema:
[
  {{
    "unit_id": "...",
    "lernziele_match": 0-100,
    "empfehlung": "vollständig"|"teilweise"|"keine",
    "lernziele": [{{"ziel": "Unit-Ziel", "status": "✓|~|✗", "note": "1 Satz"}}],
    "credits": {{"extern": Zahl|null, "intern": Zahl|null, "bewertung": "OK/Problem + 1 Satz"}},
    "niveau": "1 Satz zur Passung",
    "pruefung": "1 Satz zum Prüfungsvergleich",
    "workload": "1 Satz zur Arbeitsbelastung",
    "defizite": ["Lücke 1", "..."],
    "fazit": "2-3 Sätze, klare Begründung + Empfehlung"
  }}
]

Kriterien:
- Lernziele: ≥80% → vollständig, ≥50% → teilweise, <50% → keine
- Credits: extern ≥ intern = OK (bis ~10% Differenz tolerierbar)
- Niveau/Prüfung/Workload nur erwähnen, wenn relevant für Entscheidung
- Max 3 Defizite, sachlich, keine Floskeln.

## Externes Modul
{external_text}

## Interne Units
{units_text}
"""

        try:
            start = time.time()
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=COMPARISON_SCHEMA,
                    thinking_config=types.ThinkingConfig(thinking_budget=-1),
                ),
            )
            llm_time = time.time() - start

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

            logger.info(f"Compare LLM call completed in {llm_time:.3f}s ({len(results)} units)")
            return {
                "results": results,
                "timing": {
                    "compare_llm_ms": round(llm_time * 1000, 1)
                }
            }

        except Exception as e:
            return {"results": [{"error": str(e)}], "timing": {}}

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
