#!/usr/bin/env python3
"""Sync extracted module/unit data to Airtable."""
import json
import subprocess
import os
from pathlib import Path

# Airtable IDs
BASE_ID = 'appoawrI73padNkWy'
MODULES_TABLE = 'tblNwW2NWEnSdnyzM'
UNITS_TABLE = 'tblbUxQbNAkGRxdT0'

def call_airtable(tool: str, **kwargs) -> dict | None:
    """Call Airtable via mcporter."""
    cmd = f'source .env && AIRTABLE_API_KEY="$AIRTABLE_API_KEY" npx mcporter --config ~/.config/mcporter.json airtable.{tool}'
    for k, v in kwargs.items():
        if isinstance(v, (dict, list)):
            cmd += f" {k}='{json.dumps(v)}'"
        else:
            cmd += f" {k}={v}"

    result = subprocess.run(
        ['bash', '-c', cmd],
        capture_output=True,
        text=True,
        cwd='/Users/jonathan.glasmeyer/Projects/stephan-uni'
    )

    if result.returncode == 0:
        if result.stdout.strip():
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {'success': True}  # Some calls don't return JSON
        return {'success': True}
    else:
        print(f"  Error: {result.stderr[:200]}")
        return None


def get_existing_records(table_id: str) -> dict:
    """Get existing records from Airtable, keyed by ID field."""
    records = {}
    result = call_airtable('list_records', baseId=BASE_ID, tableId=table_id, maxRecords=200)
    if result:
        for rec in result:
            # Use Modul-ID or Unit-ID as key
            rec_id = rec['fields'].get('Modul-ID') or rec['fields'].get('Unit-ID')
            if rec_id:
                records[rec_id] = rec['id']
    return records


def update_modules(extracted_data: dict) -> dict:
    """Update Module table with extracted data."""
    print("\n=== Updating Modules ===")

    existing = get_existing_records(MODULES_TABLE)
    print(f"Found {len(existing)} existing modules in Airtable")

    updated = 0
    created = 0

    for module_id, module in extracted_data['modules'].items():
        fields = {
            'Modul-ID': module_id,
            'Titel': module.get('title', ''),
            'Credits': int(module['credits']) if module.get('credits', '').isdigit() else None,
            'SWS': int(module['sws']) if module.get('sws', '').isdigit() else None,
            'Semester': int(module['semester']) if module.get('semester', '').isdigit() else None,
            'Dauer': module.get('dauer', ''),
            'Angebotsturnus': module.get('angebotsturnus', ''),
            'Workload': module.get('workload', ''),
            'Modulart': module.get('modulart', ''),
            'Lehrsprache': module.get('lehrsprache', ''),
            'Modulkoordination': module.get('modulkoordination', ''),
            'Lernziele': module.get('gesamtziele', ''),  # Using existing field
            'Prüfungsform': module.get('pruefungsleistung', ''),  # Using existing field
            'Voraussetzungen': module.get('voraussetzungen', ''),
        }
        # Remove None/empty values
        fields = {k: v for k, v in fields.items() if v is not None and v != ''}

        if module_id in existing:
            # Update existing
            rec_id = existing[module_id]
            result = call_airtable(
                'update_records',
                baseId=BASE_ID,
                tableId=MODULES_TABLE,
                records=[{'id': rec_id, 'fields': fields}]
            )
            if result:
                updated += 1
                print(f"  Updated {module_id}")
        else:
            # Create new - but skip since we want to update existing only
            print(f"  Skipping {module_id} (not in Airtable)")

    print(f"Updated {updated} modules")
    return existing


def update_units(extracted_data: dict, module_records: dict) -> None:
    """Update Units table with extracted data."""
    print("\n=== Updating Units ===")

    existing = get_existing_records(UNITS_TABLE)
    print(f"Found {len(existing)} existing units in Airtable")

    updated = 0

    for unit_id, unit in extracted_data['units'].items():
        # Build fields
        fields = {
            'Unit-ID': unit_id,
            'Titel': unit.get('title', ''),
            'SWS': int(unit['sws']) if unit.get('sws', '').isdigit() else None,
            'Semester': int(unit['semester']) if unit.get('semester', '').isdigit() else None,
            'Workload': unit.get('workload', ''),
            'Dauer': unit.get('dauer', ''),
            'Angebotsturnus': unit.get('angebotsturnus', ''),
            'Lehrsprache': unit.get('lehrsprache', ''),
            'Lernziele': unit.get('learning_outcomes_text', ''),
            'Inhalte': unit.get('content', ''),
        }
        # Remove None/empty values
        fields = {k: v for k, v in fields.items() if v is not None and v != ''}

        if unit_id in existing:
            rec_id = existing[unit_id]
            result = call_airtable(
                'update_records',
                baseId=BASE_ID,
                tableId=UNITS_TABLE,
                records=[{'id': rec_id, 'fields': fields}]
            )
            if result:
                updated += 1
                print(f"  Updated {unit_id}")
        else:
            print(f"  Skipping {unit_id} (not in Airtable)")

    print(f"Updated {updated} units")


def main():
    # Load extracted data (use docling version)
    json_path = Path('/Users/jonathan.glasmeyer/Projects/stephan-uni/data/kern/modulhandbuecher/BA_PuMa_extracted_docling.json')

    if not json_path.exists():
        print(f"Error: {json_path} not found. Run extract_modules_from_pdf.py first.")
        return

    with open(json_path) as f:
        data = json.load(f)

    print(f"Loaded {len(data['modules'])} modules and {len(data['units'])} units from JSON")

    # First, we need to add new fields to the tables
    print("\nNote: Make sure these fields exist in Airtable:")
    print("  Module: Titel, Credits, Semester, Lernziele, Prüfungsform")
    print("  Units: Titel, SWS, Lernziele, Inhalte")

    # Update modules
    module_records = update_modules(data)

    # Update units
    update_units(data, module_records)

    print("\nDone!")


if __name__ == '__main__':
    main()
