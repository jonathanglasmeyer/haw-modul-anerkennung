#!/usr/bin/env python3
"""Extract MA PuMa modules (different format than BA).

Usage:
    python scripts/extract_modules_docling_ma.py <pdf_path> <output_json> [--prefix PREFIX]
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


def extract_modules_and_units(markdown: str, prefix: str = "MAPuMa") -> dict:
    """Parse MA format markdown (different from BA format)."""
    modules = {}
    units = {}

    # Find module sections in overview table
    module_pattern = r'\| Modul (\d+)\s*\|[^|]*\|\s*([^|]+?)\s*\|'

    for match in re.finditer(module_pattern, markdown):
        module_num = match.group(1)
        module_title = match.group(2).strip()
        module_id = f"{prefix}_M{module_num}"

        if module_id not in modules:
            modules[module_id] = {
                'id': module_id,
                'title': module_title,
                'credits': '',
                'sws': '',
                'semester': '',
                'lernziele': '',
                'pruefungsleistung': '',
                'units': []
            }

    # Find unit detail tables: "| Unit 1 | Title |"
    unit_table_pattern = r'\| Unit (\d+)\s*\|\s*([^|]+?)\s*\|'

    for match in re.finditer(unit_table_pattern, markdown):
        unit_num = match.group(1)
        unit_title = match.group(2).strip()

        # Find which module this belongs to (look backwards for "| Modul X |")
        pos = match.start()
        section_before = markdown[max(0, pos - 2000):pos]

        # Find the most recent module header
        mod_matches = list(re.finditer(r'\| Modul (\d+)', section_before))
        if not mod_matches:
            continue

        module_num = mod_matches[-1].group(1)
        module_id = f"{prefix}_M{module_num}"
        unit_id = f"{module_id}_U{unit_num}"

        if unit_id in units:
            continue

        # Get section after this unit table
        section_after = markdown[match.end():match.end() + 3000]

        # Extract metadata from table rows
        semester = extract_table_value(section_after, r'Semester[^|]*\|(?:[^|]*\|){0,3}\s*(\d+)\.\s*Semester')
        lp_sws = extract_table_value(section_after, r'(\d+)\s*LP\s*\([^)]+\)/(\d+)\s*SWS')
        workload = extract_table_value(section_after, r'Arbeitsaufwand[^|]*\|\s*([^|]+?)\s*\|')
        lehrsprache = extract_table_value(section_after, r'Lehrsprache[^|]*\|\s*(\w+)')

        # Be tolerant: if combined pattern fails, fall back to simple LP/SWS matches
        credits = ''
        sws = ''
        if lp_sws:
            credits = lp_sws.split()[0] if ' ' in lp_sws else lp_sws
            sws = lp_sws.split()[-1] if ' ' in lp_sws else ''
        if not credits:
            m = re.search(r'(\d+)\s*LP', section_after)
            credits = m.group(1) if m else ''
        if not sws:
            m = re.search(r'(\d+)\s*SWS', section_after)
            sws = m.group(1) if m else ''

        # Extract competencies
        competencies = {}
        learning_outcomes_parts = []

        # Look for competency headers: ## Fachkompetenzen, ## Methodenkompetenz, etc.
        for comp_type in ['Fachkompetenz', 'Methodenkompetenz', 'Sozialkompetenz', 'Selbstkompetenz']:
            pattern = rf'##\s*{comp_type}[^\n]*\n(.*?)(?=##\s*(?:Fach|Methoden|Sozial|Selbst)|$)'
            comp_match = re.search(pattern, section_after, re.DOTALL | re.IGNORECASE)
            if comp_match:
                content = comp_match.group(1).strip()
                # Clean up
                content = re.sub(r'^Die Studierenden\s*\n?', '', content)
                content = re.sub(r'\n\s*[-•]\s*', '\n- ', content)
                content = content[:1500]
                competencies[comp_type.lower()] = content
                if content:
                    learning_outcomes_parts.append(f"### {comp_type}\n{content}")

        # Extract Inhalte section (allow for variants like "Lerninhalte", "Inhalte des Moduls")
        content = ''
        inhalte_match = re.search(r'##\s*(?:Lerninhalte|Inhalte(?: des Moduls)?)\s*[^\n]*\n(.*?)(?=##|$)', section_after, re.DOTALL | re.IGNORECASE)
        if inhalte_match:
            content = inhalte_match.group(1).strip()[:2000]

        units[unit_id] = {
            'id': unit_id,
            'module_id': module_id,
            'unit_nr': int(unit_num),
            'title': unit_title,
            'semester': semester,
            'credits': credits,
            'sws': sws,
            'workload': workload,
            'lehrsprache': lehrsprache or 'deutsch',
            'learning_outcomes': competencies,
            'learning_outcomes_text': '\n'.join(learning_outcomes_parts),
            'content': content,
        }

        # Add to parent module
        if module_id in modules:
            if unit_id not in modules[module_id]['units']:
                modules[module_id]['units'].append(unit_id)
            # Update module metadata from first unit
            if not modules[module_id]['credits'] and credits:
                modules[module_id]['credits'] = credits
            if not modules[module_id]['semester'] and semester:
                modules[module_id]['semester'] = semester

    # Backfill missing module metadata from units (credits/semester/SWS) or module block
    from collections import Counter
    for module_id, module in modules.items():
        unit_ids = module.get('units', [])
        unit_objs = [units[uid] for uid in unit_ids if uid in units]
        if not module.get('credits'):
            for u in unit_objs:
                if u.get('credits'):
                    module['credits'] = u['credits']
                    break
        if not module.get('sws'):
            for u in unit_objs:
                if u.get('sws'):
                    module['sws'] = u['sws']
                    break
        if not module.get('semester'):
            sems = [u['semester'] for u in unit_objs if u.get('semester')]
            if sems:
                module['semester'] = Counter(sems).most_common(1)[0][0]

        # If still missing, scrape near the module block in markdown
        if not module.get('credits') or not module.get('sws') or not module.get('semester'):
            module_num = module_id.split('_M')[1]
            idx = markdown.find(f"Modul {module_num}")
            if idx != -1:
                section = markdown[idx:idx + 4000]
                if not module.get('credits'):
                    m = re.search(r'(\d+)\s*LP', section)
                    if m:
                        module['credits'] = m.group(1)
                if not module.get('sws'):
                    m = re.search(r'(\d+)\s*SWS', section)
                    if m:
                        module['sws'] = m.group(1)
                if not module.get('semester'):
                    m = re.search(r'(\d+)[\\.,]?\s*(?:und\\s*)?(\\d+)?\\s*Semester', section)
                    if m:
                        module['semester'] = m.group(1)

    return {'modules': modules, 'units': units}


def extract_table_value(text: str, pattern: str) -> str:
    """Extract value from table using regex."""
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else ''


def main():
    if len(sys.argv) < 3:
        print("Usage: extract_modules_docling_ma.py <pdf_path> <output_json> [--prefix PREFIX]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_json = sys.argv[2]

    # Parse optional prefix
    prefix = "MAPuMa"
    if "--prefix" in sys.argv:
        idx = sys.argv.index("--prefix")
        if idx + 1 < len(sys.argv):
            prefix = sys.argv[idx + 1]

    print(f"PDF: {pdf_path}")
    print(f"Output: {output_json}")
    print(f"Prefix: {prefix}\n")

    # Check if markdown cache exists
    pdf_name = Path(pdf_path).stem
    md_cache = Path(f"/tmp/{pdf_name}_ma_docling.md")

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
    print("\nExtracting modules and units (MA format)...")
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
