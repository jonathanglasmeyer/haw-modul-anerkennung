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
                "verantwortliche": meta.get("verantwortliche", ""),
                "similarity": round(similarity, 3),
                "doc": doc
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

        # Format external module and internal unit
        external_text = self._format_module_for_comparison(external_module, is_external=True)
        internal_text = f"""**Unit:** {internal_meta.get('unit_title')}
**Modul:** {internal_meta.get('module_title')}
**Credits:** {internal_meta.get('credits')}
**SWS:** {internal_meta.get('sws')}
**Workload:** {internal_meta.get('workload')}
**Prüfung:** {internal_meta.get('pruefungsleistung')}

**Inhalt:**
{internal_doc}"""

        prompt = f"""Prüfe, ob externes Modul auf interne Unit anerkennbar ist. Liefere JSON nach Schema:
{{
  "lernziele_match": 0-100,
  "empfehlung": "vollständig"|"teilweise"|"keine",
  "lernziele": [
    {{"ziel": "Unit-Ziel", "status": "✓|~|✗", "note": "1 Satz warum"}}
  ],
  "credits": {{"extern": Zahl|null, "intern": Zahl|null, "bewertung": "OK/Problem + 1 Satz"}},
  "niveau": "Bachelor/Master Bewertung, 1 Satz",
  "pruefung": "Prüfungsform-Vergleich, 1 Satz",
  "workload": "Workload-Einordnung, 1 Satz",
  "defizite": ["konkrete Lücke 1", "…"],
  "fazit": "2-3 Sätze, klare Begründung + Empfehlung"
}}

Kriterien:
- Lernziele: ≥80% → vollständig, ≥50% → teilweise, <50% → keine
- Credits: Extern ≥ Intern OK, bis ~10% Diff tolerierbar
- Niveau/Prüfung/Workload nur erwähnen wenn relevant
- Max 3 Defizite, sachlich, keine Floskeln.

## Externes Modul
{external_text}

## Interne Unit
{internal_text}"""

        try:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SINGLE_COMPARISON_SCHEMA,
                thinking_config=types.ThinkingConfig(thinking_budget=1000),
                temperature=0,  # Deterministic output
            )

            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt],
                config=config,
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
        """Compare external module with multiple internal units using parallel single calls.

        Args:
            external_module: Parsed external module data
            unit_ids: List of unit IDs to compare against

        Returns:
            List of comparison results with timing metadata
        """
        import concurrent.futures

        total_start = time.time()

        # Get all internal units
        db_start = time.time()
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
        db_time = time.time() - db_start

        if not units_data:
            return {"results": [], "timing": {}}

        # Parallel LLM calls (one per unit)
        def compare_single_unit(unit_data):
            """Helper to compare one unit."""
            llm_start = time.time()
            external_text = self._format_module_for_comparison(external_module, is_external=True)

            # Format internal unit content
            internal_text = f"""**Unit:** {unit_data['meta'].get('unit_title')}
**Modul:** {unit_data['meta'].get('module_title')}
**Credits:** {unit_data['meta'].get('credits')}
**SWS:** {unit_data['meta'].get('sws')}
**Workload:** {unit_data['meta'].get('workload')}
**Prüfung:** {unit_data['meta'].get('pruefungsleistung')}

**Inhalt:**
{unit_data['doc']}"""

            prompt = f"""Prüfe, ob externes Modul auf interne Unit anerkennbar ist. Liefere JSON nach Schema:
{{
  "unit_id": "{unit_data['unit_id']}",
  "lernziele_match": 0-100,
  "empfehlung": "vollständig"|"teilweise"|"keine",
  "lernziele": [
    {{"ziel": "Unit-Ziel", "status": "✓|~|✗", "note": "1 Satz warum"}}
  ],
  "credits": {{"extern": Zahl|null, "intern": Zahl|null, "bewertung": "OK/Problem + 1 Satz"}},
  "niveau": "Bachelor/Master Bewertung, 1 Satz",
  "pruefung": "Prüfungsform-Vergleich, 1 Satz",
  "workload": "Workload-Einordnung, 1 Satz",
  "defizite": ["konkrete Lücke 1", "…"],
  "fazit": "2-3 Sätze, klare Begründung + Empfehlung"
}}

Kriterien:
- Lernziele: ≥85% UND alle Kernlernziele → vollständig, ≥50% → teilweise, <50% → keine
- GRENZFÄLLE (75-84%): Wenn Zweifel oder Kernlernziele fehlen → IMMER "teilweise"
- Credits: Extern ≥ Intern OK, bis ~10% Diff tolerierbar
- Niveau/Prüfung/Workload nur erwähnen wenn relevant
- Max 3 Defizite, sachlich, keine Floskeln.

## Externes Modul
{external_text}

## Interne Unit
{internal_text}"""

            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SINGLE_COMPARISON_SCHEMA,
                thinking_config=types.ThinkingConfig(thinking_budget=1000),
                temperature=0,  # Deterministic output
            )

            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt],
                config=config,
            )

            content = response.candidates[0].content.parts[0].text
            result = json.loads(content)
            llm_time = time.time() - llm_start

            # Enrich with metadata
            result['unit_id'] = unit_data['unit_id']  # Add unit_id from data
            result['unit_title'] = unit_data['meta'].get('unit_title', '')
            result['module_title'] = unit_data['meta'].get('module_title', '')
            result['unit_credits'] = unit_data['meta'].get('credits')
            result['unit_sws'] = unit_data['meta'].get('sws')
            result['unit_workload'] = unit_data['meta'].get('workload')
            result['verantwortliche'] = unit_data['meta'].get('verantwortliche', '')
            result['unit_content'] = unit_data['doc'][:2000]

            return result, llm_time

        try:
            # Execute all comparisons in parallel using ThreadPoolExecutor
            llm_start = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(units_data)) as executor:
                futures = [executor.submit(compare_single_unit, u) for u in units_data]
                results_with_timing = [f.result() for f in concurrent.futures.as_completed(futures)]

            results = [r[0] for r in results_with_timing]
            llm_times = [r[1] for r in results_with_timing]
            total_llm_time = time.time() - llm_start  # Wall-clock time (parallel)
            avg_llm_time = sum(llm_times) / len(llm_times) if llm_times else 0

            total_time = time.time() - total_start

            return {
                "results": results,
                "timing": {
                    "db_ms": round(db_time * 1000, 1),
                    "llm_ms": round(total_llm_time * 1000, 1),  # Parallel wall-clock time
                    "avg_llm_per_unit_ms": round(avg_llm_time * 1000, 1),
                    "total_ms": round(total_time * 1000, 1),
                }
            }

        except Exception as e:
            logger.error(f"Error in compare_multiple: {e}")
            return {"results": [], "timing": {}, "error": str(e)}

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
