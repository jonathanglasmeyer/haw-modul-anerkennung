#!/usr/bin/env python3
"""Extract structured module/unit data from Modulhandbuch PDF via Docling or markitdown.

Usage:
    python scripts/extract_pdf_to_json.py <pdf_path> <output_json> --prefix BAPuMa
"""
import sys
import re
import json
import subprocess
from pathlib import Path


def convert_pdf_to_markdown(pdf_path: str) -> str:
    """Convert PDF to markdown using markitdown CLI."""
    print(f"Converting {pdf_path} with markitdown (this may take ~2 min)...")

    # Try markitdown first (available via document-reading skill)
    try:
        result = subprocess.run(
            ['markitdown', pdf_path],
            capture_output=True,
            text=True,
            timeout=300,
            check=True
        )
        md = result.stdout
        print(f"Converted to {len(md)} chars of markdown")
        return md
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"markitdown failed: {e}")
        print("Trying to import docling...")

        # Fallback to docling if available
        try:
            from docling.document_converter import DocumentConverter
            converter = DocumentConverter()
            result = converter.convert(pdf_path)
            md = result.document.export_to_markdown()
            print(f"Converted to {len(md)} chars of markdown")
            return md
        except ImportError:
            raise RuntimeError(
                "Neither markitdown nor docling is available. "
                "Install docling via: uv sync (after adding to pyproject.toml)"
            )


def extract_modules_and_units(markdown: str, prefix: str = "BAPuMa") -> dict:
    """Parse docling markdown and extract structured module/unit data."""
    modules = {}
    units = {}

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
        next_unit = re.search(r'\| M\d+[A-Z]? Unit \d+', markdown[start_pos:])
        end_pos = start_pos + next_unit.start() if next_unit else min(start_pos + 5000, len(markdown))
        section = markdown[start_pos:end_pos]

        # Extract metadata from table rows
        semester = extract_table_value(section, r'Semester[^|]*\|[^|]*\|[^|]*\|\s*(\d+)\. Semester')
        sws = extract_table_value(section, r'(\d+)\s*SWS')
        workload = extract_table_value(section, r'(Präsenzstudium\s*\d+\s*h,?\s*Selbststudium\s*\d+\s*h)')
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

        # Format as markdown sections
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
            'lehrsprache': lehrsprache,
            'learning_outcomes': learning_outcomes,
            'learning_outcomes_text': '\n'.join(all_outcomes),
            'content': content,
        }

        # Skip duplicates
        if unit_id not in units:
            units[unit_id] = unit_data

            # Add to module
            if module_id not in modules:
                modules[module_id] = {
                    'id': module_id,
                    'title': '',
                    'credits': '',
                    'sws': '',
                    'semester': '',
                    'units': []
                }
            if unit_id not in modules[module_id]['units']:
                modules[module_id]['units'].append(unit_id)

    # Extract module-level info from module headers
    module_pattern = r'\| Modul (\d+[A-Z]?) \(M\d+[A-Z]?\)\s*\|[^|]*\|[^|]*\|\s*([^|]+?)\s*\|'

    seen_modules = set()
    for match in re.finditer(module_pattern, markdown):
        module_num = match.group(1)
        module_title = match.group(2).strip()
        module_id = f"{prefix}_M{module_num}"

        if module_id in seen_modules:
            continue
        seen_modules.add(module_id)

        # Get section after module header
        start_pos = match.start()
        next_section = re.search(r'\| Modul \d+[A-Z]? \(M\d+', markdown[match.end():])
        end_pos = match.end() + next_section.start() if next_section else min(match.end() + 8000, len(markdown))
        section = markdown[start_pos:end_pos]

        # Extract module metadata
        credits_match = re.search(r'(\d+)\s*LP', section)
        credits = credits_match.group(1) if credits_match else ''

        sws_match = re.search(r'(\d+)\s*SWS', section)
        sws = sws_match.group(1) if sws_match else ''

        semester = extract_table_value(section, r'Semester[^|]*\|[^|]*\|[^|]*\|\s*(\d+)\. Semester')
        lernziele = extract_gesamtziele(section)
        pruefung = extract_pruefungsleistung(section)

        module_data = {
            'id': module_id,
            'title': module_title,
            'credits': credits,
            'sws': sws,
            'semester': semester,
            'lernziele': lernziele,
            'pruefungsleistung': pruefung,
            'units': []
        }

        if module_id in modules:
            existing_units = modules[module_id].get('units', [])
            modules[module_id] = module_data
            modules[module_id]['units'] = existing_units
        else:
            modules[module_id] = module_data

    return {'modules': modules, 'units': units}


def extract_gesamtziele(text: str) -> str:
    """Extract Gesamtziele section from module."""
    pattern = r'##\s*Gesamtziele\s*\n(.*?)(?=##\s*Zu erwerbende|##\s*Inhalte|\| M\d+|$)'
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not match:
        return ''

    content = match.group(1).strip()
    content = re.sub(r'^##\s*Die Studierenden\s*\n?', '', content)
    content = re.sub(r'\n\s*[-•]\s*', '\n- ', content)
    content = re.sub(r'^[-•]\s*', '- ', content)
    return content[:2000]


def extract_pruefungsleistung(text: str) -> str:
    """Extract Prüfungsleistung from module section."""
    pattern = r'Voraussetzung für die Vergabe von Leistungspunkten[^|]*\|\s*([^|]+?)\s*\|'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        result = match.group(1).strip()
        result = re.sub(r'\s+', ' ', result)
        return result[:500]

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
    pattern = rf'##\s*{comp_type}[^\n]*\n(.*?)(?=##\s*(?:Fach|Methoden|Sozial|Selbst)kompetenz|##\s*Inhalte|$)'
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not match:
        return ''

    content = match.group(1).strip()
    content = re.sub(r'^Die Studierenden\s*(können|kennen|sind[^,]*,?)\s*', '', content)
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
    content = re.sub(r'\n\s*[-•]\s*', '\n- ', content)
    content = re.sub(r'^[-•]\s*', '- ', content)
    return content[:2000]


def main():
    if len(sys.argv) < 3:
        print("Usage: extract_pdf_to_json.py <pdf_path> <output_json> [--prefix PREFIX]")
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
