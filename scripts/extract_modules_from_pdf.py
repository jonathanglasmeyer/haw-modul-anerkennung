#!/usr/bin/env python3
"""Extract structured module/unit data from Modulhandbuch PDF (via markdown)."""
import re
import json
from pathlib import Path

def extract_modules_and_units(markdown_path: str) -> dict:
    """Parse module handbook markdown and extract structured data."""

    with open(markdown_path, 'r') as f:
        content = f.read()

    modules = {}
    units = {}

    # Split into sections by "Modul X (MX)" headers
    # Pattern: "Modul 2 (M2)\n\nMethodische Grundlagen\n\nModulkoordination"
    module_pattern = r'(Modul (\d+[A-Z]?) \(M\d+[A-Z]?(?:-R)?\))\s*\n\s*\n([^\n]+)\s*\n\s*\n(?:Modulkoordination|Semester)'

    # Find all module headers with their titles
    for match in re.finditer(module_pattern, content):
        module_header = match.group(1)
        module_num = match.group(2)
        module_title = match.group(3).strip()

        module_id = f"BAPuMa_M{module_num}"
        if module_id in modules:  # Skip duplicates
            continue

        # Get the section content after this header
        start_pos = match.end()
        # Find next module header or end
        next_module = re.search(r'\nModul \d+[A-Z]? \(M\d+', content[start_pos:])
        end_pos = start_pos + next_module.start() if next_module else len(content)
        section = content[start_pos:end_pos]

        # Extract module metadata
        module_data = {
            'id': module_id,
            'title': module_title,
            'credits': extract_field(section, r'Leistungspunkte.*?(\d+)\s*LP'),
            'semester': extract_field(section, r'Semester\s*\n\s*(\d+)\. Semester'),
            'workload': extract_field(section, r'Arbeitsaufwand.*?\n\s*([^\n]+)'),
            'goals': extract_multiline(section, r'Gesamtziele\s*\n(.*?)(?=Zu erwerbende|Inhalte|$)'),
            'assessment': extract_field(section, r'((?:Portfolio|Klausur|Hausarbeit|Referat)[^\n]*)'),
            'responsible': extract_profs(section),
            'units': []
        }

        modules[module_id] = module_data

    # Now extract unit details
    # Units appear as "M1 Unit 1" sections with detailed info
    unit_section_pattern = r'(M(\d+[A-Z]?) Unit (\d+))\s*\n\s*\n?([^\n]+?)(?:\s*\n\s*\n|\s*\()'

    for match in re.finditer(unit_section_pattern, content):
        unit_header = match.group(1)
        module_num = match.group(2)
        unit_num = match.group(3)
        unit_title = match.group(4).strip()

        module_id = f"BAPuMa_M{module_num}"
        unit_id = f"BAPuMa_M{module_num}_U{unit_num}"

        # Get section content
        start_pos = match.end()
        # Find next unit or module header
        next_section = re.search(r'\n(?:M\d+[A-Z]? Unit \d+|Modul \d+)', content[start_pos:])
        end_pos = start_pos + next_section.start() if next_section else min(start_pos + 3000, len(content))
        section = content[start_pos:end_pos]

        # Extract learning outcomes by competency type
        learning_outcomes = {
            'fachkompetenz': extract_competency(section, 'Fachkompetenz'),
            'methodenkompetenz': extract_competency(section, 'Methodenkompetenz'),
            'sozialkompetenz': extract_competency(section, 'Sozialkompetenz'),
            'selbstkompetenz': extract_competency(section, 'Selbstkompetenz'),
        }

        # Combine all learning outcomes into one text
        all_outcomes = []
        for comp_type, outcomes in learning_outcomes.items():
            if outcomes:
                all_outcomes.append(f"[{comp_type}] {outcomes}")

        unit_data = {
            'id': unit_id,
            'module_id': module_id,
            'unit_nr': int(unit_num),
            'title': unit_title,
            'sws': extract_field(section, r'(\d+)\s*SWS'),
            'workload': extract_field(section, r'Arbeitsaufwand.*?\n\s*([^\n]+)'),
            'learning_outcomes': learning_outcomes,
            'learning_outcomes_text': '\n'.join(all_outcomes),
            'content': extract_multiline(section, r'Inhalte der Unit\s*\n(.*?)(?=Literatur|Lehr-|$)'),
        }

        units[unit_id] = unit_data

        # Add to parent module
        if module_id in modules:
            modules[module_id]['units'].append(unit_id)

    return {'modules': modules, 'units': units}


def extract_field(text: str, pattern: str) -> str:
    """Extract a single field using regex."""
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ''


def extract_multiline(text: str, pattern: str) -> str:
    """Extract multiline content, clean up bullet points."""
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not match:
        return ''
    content = match.group(1).strip()
    # Clean up bullet points
    content = re.sub(r'\n\s*•\s*', '\n• ', content)
    content = re.sub(r'\n\s+', '\n', content)
    return content[:2000]  # Limit length


def extract_competency(text: str, comp_type: str) -> str:
    """Extract a specific competency section."""
    # Pattern: "Fachkompetenz (...)...Die Studierenden...• bullet points"
    pattern = rf'{comp_type}[^\n]*\n(.*?)(?=(?:Methoden|Sozial|Selbst|Fach)kompetenz|Inhalte|Literatur|Lehr-|$)'
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not match:
        return ''
    content = match.group(1).strip()
    # Remove "Die Studierenden" prefix variations
    content = re.sub(r'^Die Studierenden\s*(sind in der Lage,?\s*|können\s*|)', '', content)
    # Clean bullets
    content = re.sub(r'\s*•\s*', '\n• ', content)
    content = re.sub(r'\n\s+', '\n', content)
    return content.strip()[:1500]


def extract_profs(text: str) -> list:
    """Extract professor names."""
    profs = []
    # Look for "Prof. Dr. Name" patterns
    for match in re.finditer(r'Prof\. Dr\. (?:Dr\. )?([A-Za-zäöüß\-]+)', text):
        name = match.group(1)
        if name not in profs and name not in ['Prof', 'Dr']:
            profs.append(name)
    return profs


def main():
    # Process BA PuMa
    md_path = '/tmp/ba_puma_mhb.md'

    print("Extracting modules and units from BA PuMa Modulhandbuch...")
    data = extract_modules_and_units(md_path)

    print(f"\nFound {len(data['modules'])} modules and {len(data['units'])} units")

    # Print sample
    print("\n=== Sample Module ===")
    if data['modules']:
        sample_mod = list(data['modules'].values())[0]
        print(json.dumps(sample_mod, indent=2, ensure_ascii=False)[:1000])

    print("\n=== Sample Unit ===")
    if data['units']:
        sample_unit = list(data['units'].values())[0]
        print(json.dumps(sample_unit, indent=2, ensure_ascii=False)[:1500])

    # Save to JSON
    output_path = Path('/Users/jonathan.glasmeyer/Projects/stephan-uni/data/kern/modulhandbuecher/BA_PuMa_extracted.json')
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nSaved to {output_path}")

    # Stats
    units_with_outcomes = sum(1 for u in data['units'].values() if u['learning_outcomes_text'])
    print(f"Units with learning outcomes: {units_with_outcomes}/{len(data['units'])}")


if __name__ == '__main__':
    main()
