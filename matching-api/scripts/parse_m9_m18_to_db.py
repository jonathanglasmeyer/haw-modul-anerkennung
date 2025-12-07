#!/usr/bin/env python3
"""Parse M9/M18 Wahlpflichtmodule from markdown and insert into NeonDB."""
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import types
from matching.database import get_session
from matching.models import Module, Unit

# Read the markdown sections
with open('/tmp/m9_m18_combined.txt', 'r') as f:
    markdown_text = f.read()

# Configure Gemini
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

# Prompt for LLM to extract structured data
prompt = f"""Extract structured data for modules M9 and M18 from this German Modulhandbuch markdown.

These are Wahlpflichtmodule (elective modules) where students choose seminars.

For each module, extract:
- module_id (e.g., "BAPuMa_M9")
- title
- credits (LP)
- sws
- semester
- units (array of units with unit_id, title, sws)

For M9: There are 3 units (M9 Unit 1, M9 Unit 2, M9 Unit 3)
For M18: There are 2 units (M18 Unit 1, M18 Unit 2)

Return ONLY valid JSON in this format:
{{
  "modules": {{
    "BAPuMa_M9": {{"id": "BAPuMa_M9", "title": "...", "credits": 6, "sws": 6, "semester": 1, "units": ["BAPuMa_M9_U1", "BAPuMa_M9_U2", "BAPuMa_M9_U3"]}},
    "BAPuMa_M18": {{...}}
  }},
  "units": {{
    "BAPuMa_M9_U1": {{"id": "BAPuMa_M9_U1", "module_id": "BAPuMa_M9", "unit_nr": 1, "title": "Seminar", "sws": 2}},
    ...
  }}
}}

Markdown:
{markdown_text}"""

# Call Gemini
response = client.models.generate_content(
    model='gemini-2.0-flash-exp',
    contents=prompt
)
response_text = response.text.strip()

# Extract JSON from markdown code blocks if present
if '```json' in response_text:
    response_text = response_text.split('```json')[1].split('```')[0].strip()
elif '```' in response_text:
    response_text = response_text.split('```')[1].split('```')[0].strip()

data = json.loads(response_text)

print("Parsed data:")
print(json.dumps(data, indent=2, ensure_ascii=False))

# Insert into NeonDB
session = get_session()

try:
    # Insert/update modules
    for module_id, module_data in data['modules'].items():
        existing = session.query(Module).filter(Module.module_id == module_id).first()

        if existing:
            print(f"Module {module_id} already exists, updating...")
            existing.title = module_data.get('title', existing.title)
            existing.credits = module_data.get('credits', existing.credits)
            existing.sws = module_data.get('sws', existing.sws)
            existing.semester = module_data.get('semester', existing.semester)
        else:
            print(f"Creating module {module_id}...")
            module = Module(
                module_id=module_id,
                title=module_data['title'],
                credits=module_data.get('credits'),
                sws=module_data.get('sws'),
                semester=module_data.get('semester'),
            )
            session.add(module)
            session.flush()

    session.commit()

    # Get module DB objects for FK references
    module_map = {}
    for module_id in data['modules'].keys():
        module_map[module_id] = session.query(Module).filter(Module.module_id == module_id).first()

    # Insert/update units
    for unit_id, unit_data in data['units'].items():
        existing = session.query(Unit).filter(Unit.unit_id == unit_id).first()

        module_id = unit_data['module_id']
        module = module_map[module_id]

        if existing:
            print(f"Unit {unit_id} already exists, updating...")
            existing.title = unit_data.get('title', existing.title)
            existing.sws = unit_data.get('sws', existing.sws)
        else:
            print(f"Creating unit {unit_id}...")
            unit = Unit(
                unit_id=unit_id,
                title=unit_data['title'],
                module_id=module.id,
                sws=unit_data.get('sws'),
                semester=unit_data.get('semester'),
            )
            session.add(unit)

    session.commit()
    print("\n✓ Successfully inserted M9/M18 modules and units!")

except Exception as e:
    session.rollback()
    print(f"\n❌ Error: {e}")
    raise
finally:
    session.close()
