#!/usr/bin/env python3
"""Extract structured module/unit data from Modulhandbuch PDF using Docling.

Usage:
    python scripts/extract_modules_docling.py <pdf_path> <output_json> [--prefix PREFIX]
"""
import sys
import re
import json
from pathlib import Path
from docling.document_converter import DocumentConverter


def convert_pdf_to_markdown(pdf_path: str) -> str:
    """Convert PDF to markdown using Docling."""
    print(f"Converting {pdf_path} with Docling (this may take ~2 min)...")
    converter = DocumentConverter()
    result = converter.convert(pdf_path)
    md = result.document.export_to_markdown()
    print(f"Converted to {len(md)} chars of markdown")
    return md


def extract_modules_and_units(markdown: str, prefix: str = "BAPuMa") -> dict:
    """Parse docling markdown and extract structured module/unit data."""
    modules = {}
    units = {}

    # Split by unit sections - Docling creates tables with unit headers
    # Pattern: "| M12 Unit 1 | ... | Öffentliche Finanzwirtschaft III |"

    # Find all unit table headers
    unit_pattern = r'\| (M(\d+[A-Z]?)) Unit (\d+)\s*\|[^|]*\|[^|]*\|\s*([^|]+?)\s*\|'

    for match in re.finditer(unit_pattern, markdown):
        module_short = match.group(1)  # M12
        module_num = match.group(2)    # 12
        unit_num = match.group(3)      # 1
        unit_title = match.group(4).strip()

        module_id = f"{prefix}_M{module_num}"
        unit_id = f"{prefix}_M{module_num}_U{unit_num}"

        # Get section after this match until next unit or module
        start_pos = match.end()
        # Find next unit header or end
        next_unit = re.search(r'\| M\d+[A-Z]? Unit \d+', markdown[start_pos:])
        end_pos = start_pos + next_unit.start() if next_unit else min(start_pos + 5000, len(markdown))
        section = markdown[start_pos:end_pos]

        # Extract metadata from table rows
        semester = extract_table_value(section, r'Semester[^|]*\|[^|]*\|[^|]*\|\s*(\d+)\. Semester')
        if not semester:
            m_sem = re.search(r'(\d+)\.\s*Semester', section)
            semester = m_sem.group(1) if m_sem else ''
        if not semester:
            m_sem = re.search(r'Fachsemester[^|]*\|\s*(\d+)', section)
            semester = m_sem.group(1) if m_sem else ''
        sws = extract_table_value(section, r'(\d+)\s*SWS')
        workload = extract_table_value(section, r'(Präsenzstudium\s*\d+\s*h,?\s*Selbststudium\s*\d+\s*h)')
        dauer = extract_table_value(section, r'\|\s*Dauer\s*\|[^|]*\|\s*(\d+\s*Semester)')
        angebotsturnus = extract_table_value(section, r'\|\s*(jedes\s+(?:Sommer|Winter)semester)\s*\|')
        lehrsprache = extract_table_value(section, r'Lehrsprache[^|]*\|[^|]*\|[^|]*\|\s*(\w+)')

        # Extract competencies from markdown headers
        fachkompetenz = extract_competency_section(section, 'Fachkompetenz')
        methodenkompetenz = extract_competency_section(section, 'Methodenkompetenz')
        sozialkompetenz = extract_competency_section(section, 'Sozialkompetenz')
        selbstkompetenz = extract_competency_section(section, 'Selbstkompetenz')

        # Extract content
        content = extract_content_section(section)

        # Combine learning outcomes
        learning_outcomes = {
            'fachkompetenz': fachkompetenz,
            'methodenkompetenz': methodenkompetenz,
            'sozialkompetenz': sozialkompetenz,
            'selbstkompetenz': selbstkompetenz,
        }

        # Format as Airtable Rich Text Markdown
        competency_titles = {
            'fachkompetenz': 'Fachkompetenz',
            'methodenkompetenz': 'Methodenkompetenz',
            'sozialkompetenz': 'Sozialkompetenz',
            'selbstkompetenz': 'Selbstkompetenz',
        }
        all_outcomes = []
        for comp_type, outcomes in learning_outcomes.items():
            if outcomes:
                title = competency_titles.get(comp_type, comp_type)
                all_outcomes.append(f"### {title}\n{outcomes}")

        unit_data = {
            'id': unit_id,
            'module_id': module_id,
            'unit_nr': int(unit_num),
            'title': unit_title,
            'semester': semester,
            'sws': sws,
            'workload': workload,
            'dauer': dauer,
            'angebotsturnus': angebotsturnus,
            'lehrsprache': lehrsprache,
            'learning_outcomes': learning_outcomes,
            'learning_outcomes_text': '\n'.join(all_outcomes),
            'content': content,
        }

        # Skip duplicates (docling sometimes creates multiple tables for same unit)
        if unit_id not in units:
            units[unit_id] = unit_data

            # Add to module
            if module_id not in modules:
                modules[module_id] = {
                    'id': module_id,
                    'title': '',  # Will be filled from module header
                    'units': []
                }
            if unit_id not in modules[module_id]['units']:
                modules[module_id]['units'].append(unit_id)

    # Extract module-level info from module headers
    # Pattern: "| Modul 12 (M12) | ... | Interne und externe Ressourcensteuerung |"
    # Only match actual module headers (followed by Modulkoordination row)
    # Allow headers with or without the explicit "(M12)" part
    module_pattern = r'\| Modul (\d+[A-Z]?)(?: \(M\d+[A-Z]?\))?\s*\|[^|]*\|[^|]*\|\s*([^|]+?)\s*\|'

    for match in re.finditer(module_pattern, markdown):
        module_num = match.group(1)
        module_title = match.group(2).strip()
        module_id = f"{prefix}_M{module_num}"

        # Get section after module header until next module or unit header
        start_pos = match.start()
        # Find next module header or first unit of next module
        next_section = re.search(r'\| Modul \d+[A-Z]? \(M\d+', markdown[match.end():])
        end_pos = match.end() + next_section.start() if next_section else min(match.end() + 8000, len(markdown))
        section = markdown[start_pos:end_pos]

        # Extract module metadata from table rows
        credits_match = re.search(r'(\d+)\s*LP', section)
        credits = credits_match.group(1) if credits_match else ''

        sws_match = re.search(r'(\d+)\s*SWS', section)
        sws = sws_match.group(1) if sws_match else ''

        semester = extract_table_value(section, r'Semester[^|]*\|[^|]*\|[^|]*\|\s*(\d+)\. Semester')
        if not semester:
            m_sem = re.search(r'(\d+)\.\s*Semester', section)
            semester = m_sem.group(1) if m_sem else ''
        if not semester:
            m_sem = re.search(r'Fachsemester[^|]*\|\s*(\d+)', section)
            semester = m_sem.group(1) if m_sem else ''
        if not semester:
            m_sem = re.search(r'(\d+)\.\s*Semester', section)
            semester = m_sem.group(1) if m_sem else ''
        dauer = extract_table_value(section, r'\|\s*Dauer\s*\|[^|]*\|\s*(\d+\s*Semester)')
        angebotsturnus = extract_table_value(section, r'\|\s*(jedes\s+(?:Sommer|Winter)semester)\s*\|')
        workload = extract_table_value(section, r'Arbeitsaufwand[^|]*\|[^|]*\|[^|]*\|\s*(Präsenzstudium[^|]+)')
        modulart = extract_table_value(section, r'Art des Moduls[^|]*\|[^|]*\|[^|]*\|\s*(\w+modul)')
        lehrsprache = extract_table_value(section, r'Lehrsprache[^|]*\|[^|]*\|[^|]*\|\s*(\w+)')

        # Extract Modulkoordination (professors)
        modulkoord_match = re.search(r'Modulkoordination[^|]*\|[^|]*\|[^|]*\|\s*([^|]+?)\s*\|', section)
        modulkoordination = modulkoord_match.group(1).strip() if modulkoord_match else ''

        # Extract Gesamtziele section
        gesamtziele = extract_gesamtziele(section)

        # Extract Prüfungsleistungen
        pruefung = extract_pruefungsleistung(section)

        # Extract Teilnahmevoraussetzungen
        voraussetzungen_match = re.search(r'Teilnahmevoraussetzungen[^|]*\|[^|]*\|[^|]*\|\s*([^|]+?)\s*\|', section, re.DOTALL)
        voraussetzungen = voraussetzungen_match.group(1).strip()[:500] if voraussetzungen_match else ''

        module_data = {
            'id': module_id,
            'title': module_title,
            'credits': credits,
            'sws': sws,
            'semester': semester,
            'dauer': dauer,
            'angebotsturnus': angebotsturnus,
            'workload': workload,
            'modulart': modulart,
            'lehrsprache': lehrsprache,
            'modulkoordination': modulkoordination,
            'gesamtziele': gesamtziele,
            'pruefungsleistung': pruefung,
            'voraussetzungen': voraussetzungen,
            'units': []
        }

        if module_id in modules:
            existing = modules[module_id]
            existing_units = existing.get('units', [])
            module_data['units'] = existing_units
            # Merge fields, avoid overwriting with empties
            for key, value in module_data.items():
                if key == 'title':
                    current = existing.get(key, '')
                    module_data[key] = current if len(current) >= len(value) else value
                else:
                    if not value and existing.get(key):
                        module_data[key] = existing[key]
        modules[module_id] = module_data

    # Backfill missing module metadata from units (semester/credits/sws)
    from collections import Counter
    for module_id, module in modules.items():
        unit_ids = module.get('units', [])
        unit_objs = [units[uid] for uid in unit_ids if uid in units]
        if not module.get('semester'):
            sems = [u['semester'] for u in unit_objs if u.get('semester')]
            if sems:
                module['semester'] = Counter(sems).most_common(1)[0][0]
        if not module.get('credits'):
            for u in unit_objs:
                # credits are not stored on units today; keep hook for future
                if u.get('credits'):
                    module['credits'] = u['credits']
                    break
        if not module.get('sws'):
            for u in unit_objs:
                if u.get('sws'):
                    module['sws'] = u['sws']
                    break

    return {'modules': modules, 'units': units}


def extract_gesamtziele(text: str) -> str:
    """Extract Gesamtziele section from module."""
    pattern = r'##\s*Gesamtziele\s*\n(.*?)(?=##\s*Zu erwerbende|##\s*Inhalte|\| M\d+|$)'
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not match:
        return ''

    content = match.group(1).strip()
    # Remove "## Die Studierenden" sub-header if present
    content = re.sub(r'^##\s*Die Studierenden\s*\n?', '', content)
    # Normalize bullet points
    content = re.sub(r'\n\s*[-•]\s*', '\n- ', content)
    content = re.sub(r'^[-•]\s*', '- ', content)
    return content[:2000]


def extract_pruefungsleistung(text: str) -> str:
    """Extract Prüfungsleistung from module section."""
    # Look for "Voraussetzung für die Vergabe von Leistungspunkten" field
    pattern = r'Voraussetzung für die Vergabe von Leistungspunkten[^|]*\|\s*([^|]+?)\s*\|'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        result = match.group(1).strip()
        # Clean up common artifacts
        result = re.sub(r'\s+', ' ', result)
        return result[:500]

    # Alternative: look for Modulprüfung section
    pattern2 = r'##\s*Modulprüfung\s*\n(.*?)(?=##|$)'
    match2 = re.search(pattern2, text, re.IGNORECASE | re.DOTALL)
    if match2:
        return match2.group(1).strip()[:500]

    return ''


def extract_table_value(text: str, pattern: str) -> str:
    """Extract value from table row."""
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else ''


def extract_competency_section(text: str, comp_type: str) -> str:
    """Extract competency section from markdown headers."""
    # Look for "## Fachkompetenz" or similar headers
    pattern = rf'##\s*{comp_type}[^\n]*\n(.*?)(?=##\s*(?:Fach|Methoden|Sozial|Selbst)kompetenz|##\s*Inhalte|$)'
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not match:
        return ''

    content = match.group(1).strip()
    # Clean up "Die Studierenden können/kennen/sind"
    content = re.sub(r'^Die Studierenden\s*(können|kennen|sind[^,]*,?)\s*', '', content)
    # Normalize bullet points to Airtable Markdown format
    content = re.sub(r'\n\s*[-•]\s*', '\n- ', content)
    content = re.sub(r'^[-•]\s*', '- ', content)
    return content[:1500]


def extract_content_section(text: str) -> str:
    """Extract 'Inhalte der Unit' section."""
    pattern = r'##\s*Inhalte der Unit\s*\n(.*?)(?=\||\n##|$)'
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not match:
        return ''

    content = match.group(1).strip()
    # Normalize bullet points to Airtable Markdown format
    content = re.sub(r'\n\s*[-•]\s*', '\n- ', content)
    content = re.sub(r'^[-•]\s*', '- ', content)
    return content[:2000]


def main():
    if len(sys.argv) < 3:
        print("Usage: extract_modules_docling.py <pdf_path> <output_json> [--prefix PREFIX]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_json = sys.argv[2]

    # Parse optional prefix
    prefix = "BAPuMa"
    if "--prefix" in sys.argv:
        idx = sys.argv.index("--prefix")
        if idx + 1 < len(sys.argv):
            prefix = sys.argv[idx + 1]

    print(f"PDF: {pdf_path}")
    print(f"Output: {output_json}")
    print(f"Prefix: {prefix}\n")

    # Check if markdown cache exists
    pdf_name = Path(pdf_path).stem
    md_cache = Path(f"/tmp/{pdf_name}_docling.md")

    # Use cached markdown if available, otherwise convert
    if md_cache.exists():
        print(f"Using cached markdown from {md_cache}")
        with open(md_cache, 'r') as f:
            markdown = f.read()
    else:
        markdown = convert_pdf_to_markdown(pdf_path)
        with open(md_cache, 'w') as f:
            f.write(markdown)
        print(f"Saved markdown to {md_cache}")

    # Extract structured data
    print("\nExtracting modules and units...")
    data = extract_modules_and_units(markdown, prefix)

    print(f"Found {len(data['modules'])} modules and {len(data['units'])} units")

    # Save to JSON
    output_path = Path(output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Saved to {output_path}")

    # Stats
    units_with_outcomes = sum(1 for u in data['units'].values() if u['learning_outcomes_text'])
    units_with_content = sum(1 for u in data['units'].values() if u['content'])
    print(f"\nStats:")
    print(f"  Units with learning outcomes: {units_with_outcomes}/{len(data['units'])}")
    print(f"  Units with content: {units_with_content}/{len(data['units'])}")


if __name__ == '__main__':
    main()
