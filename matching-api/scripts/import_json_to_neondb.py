#!/usr/bin/env python3
"""Import extracted JSON data into NeonDB with UPSERT (no duplicates).

Usage:
    uv run --env-file .env python scripts/import_json_to_neondb.py <json_path>
"""
import sys
import os
import json
from pathlib import Path
from typing import Dict, Set

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from matching.database import get_session
from matching.models import Person, Module, Unit
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert


def upsert_personen(session, personen_names: Set[str]) -> Dict[str, Person]:
    """Insert or update Personen, return name->Person mapping."""
    print(f"Step 1: Upserting {len(personen_names)} Personen...")
    personen_map = {}
    personen_created = 0
    personen_existing = 0

    for name in personen_names:
        # Check if exists
        existing = session.execute(
            select(Person).where(Person.name == name)
        ).scalar_one_or_none()

        if existing:
            personen_map[name] = existing
            personen_existing += 1
        else:
            person = Person(name=name)
            session.add(person)
            session.flush()
            personen_map[name] = person
            personen_created += 1

    session.commit()
    print(f"  ✓ Created {personen_created} new personen")
    print(f"  ✓ Found {personen_existing} existing personen\n")

    return personen_map


def upsert_modules(session, modules_data: dict) -> Dict[str, Module]:
    """Insert or update Modules, return module_id->Module mapping."""
    print(f"Step 2: Upserting {len(modules_data)} Modules...")
    module_map = {}
    modules_created = 0
    modules_updated = 0

    for module_id, module_data in modules_data.items():
        # Check if exists
        existing = session.execute(
            select(Module).where(Module.module_id == module_id)
        ).scalar_one_or_none()

        if existing:
            # Update if we have more data now
            if module_data.get('title'):
                existing.title = module_data['title']
            if module_data.get('credits'):
                existing.credits = int(module_data['credits']) if str(module_data['credits']).isdigit() else None
            if module_data.get('sws'):
                existing.sws = int(module_data['sws']) if str(module_data['sws']).isdigit() else None
            if module_data.get('semester'):
                existing.semester = int(module_data['semester']) if str(module_data['semester']).isdigit() else None
            if module_data.get('lernziele'):
                existing.lernziele = module_data['lernziele']
            if module_data.get('pruefungsleistung'):
                existing.pruefungsleistung = module_data['pruefungsleistung']

            module_map[module_id] = existing
            modules_updated += 1
        else:
            module = Module(
                module_id=module_id,
                title=module_data.get('title', ''),
                credits=int(module_data['credits']) if module_data.get('credits') and str(module_data['credits']).isdigit() else None,
                sws=int(module_data['sws']) if module_data.get('sws') and str(module_data['sws']).isdigit() else None,
                semester=int(module_data['semester']) if module_data.get('semester') and str(module_data['semester']).isdigit() else None,
                lernziele=module_data.get('lernziele'),
                pruefungsleistung=module_data.get('pruefungsleistung'),
            )
            session.add(module)
            session.flush()
            module_map[module_id] = module
            modules_created += 1

    session.commit()
    print(f"  ✓ Created {modules_created} new modules")
    print(f"  ✓ Updated {modules_updated} existing modules\n")

    return module_map


def upsert_units(session, units_data: dict, module_map: Dict[str, Module], personen_map: Dict[str, Person]):
    """Insert or update Units with their relationships."""
    print(f"Step 3: Upserting {len(units_data)} Units...")
    units_created = 0
    units_updated = 0
    units_skipped = 0

    for unit_id, unit_data in units_data.items():
        # Get module reference
        module_id = unit_data.get('module_id')
        if not module_id or module_id not in module_map:
            print(f"  ⚠ Skipping unit {unit_id}: missing module reference")
            units_skipped += 1
            continue

        module = module_map[module_id]

        # Check if exists
        existing = session.execute(
            select(Unit).where(Unit.unit_id == unit_id)
        ).scalar_one_or_none()

        if existing:
            # Update fields
            if unit_data.get('title'):
                existing.title = unit_data['title']
            if unit_data.get('semester'):
                existing.semester = int(unit_data['semester']) if str(unit_data['semester']).isdigit() else None
            if unit_data.get('sws'):
                existing.sws = int(unit_data['sws']) if str(unit_data['sws']).isdigit() else None
            if unit_data.get('workload'):
                existing.workload = unit_data['workload']
            if unit_data.get('lehrsprache'):
                existing.lehrsprache = unit_data['lehrsprache']
            if unit_data.get('learning_outcomes_text'):
                existing.lernziele = unit_data['learning_outcomes_text']
            if unit_data.get('content'):
                existing.inhalte = unit_data['content']

            # Update verantwortliche if provided
            verantwortliche_names = unit_data.get('verantwortliche', [])
            if verantwortliche_names:
                existing.verantwortliche.clear()
                for name in verantwortliche_names:
                    if name in personen_map:
                        existing.verantwortliche.append(personen_map[name])

            units_updated += 1
        else:
            # Create new unit
            unit = Unit(
                unit_id=unit_id,
                title=unit_data.get('title', ''),
                module_id=module.id,
                semester=int(unit_data['semester']) if unit_data.get('semester') and str(unit_data['semester']).isdigit() else None,
                sws=int(unit_data['sws']) if unit_data.get('sws') and str(unit_data['sws']).isdigit() else None,
                workload=unit_data.get('workload'),
                lehrsprache=unit_data.get('lehrsprache'),
                lernziele=unit_data.get('learning_outcomes_text'),
                inhalte=unit_data.get('content'),
            )

            # Add verantwortliche relationships
            verantwortliche_names = unit_data.get('verantwortliche', [])
            for name in verantwortliche_names:
                if name in personen_map:
                    unit.verantwortliche.append(personen_map[name])

            session.add(unit)
            units_created += 1

    session.commit()
    print(f"  ✓ Created {units_created} new units")
    print(f"  ✓ Updated {units_updated} existing units")
    if units_skipped > 0:
        print(f"  ⚠ Skipped {units_skipped} units (missing module reference)\n")
    else:
        print()


def import_json(json_path: str):
    """Import JSON data into NeonDB."""
    print(f"=== Importing {json_path} → NeonDB ===\n")

    # Load JSON
    with open(json_path, 'r') as f:
        data = json.load(f)

    modules_data = data.get('modules', {})
    units_data = data.get('units', {})

    print(f"Found {len(modules_data)} modules and {len(units_data)} units\n")

    if not modules_data or not units_data:
        print("No data to import!")
        return

    session = get_session()

    try:
        # Extract personen names from units (if verantwortliche field exists)
        personen_names: Set[str] = set()
        for unit in units_data.values():
            verantwortliche = unit.get('verantwortliche', [])
            personen_names.update(verantwortliche)

        # Step 1: Upsert Personen
        personen_map = {}
        if personen_names:
            personen_map = upsert_personen(session, personen_names)
        else:
            print("Step 1: No personen to import\n")

        # Step 2: Upsert Modules
        module_map = upsert_modules(session, modules_data)

        # Step 3: Upsert Units
        upsert_units(session, units_data, module_map, personen_map)

        # Summary
        print("=== Import Complete ===")
        print(f"Total Personen: {len(personen_map)}")
        print(f"Total Modules:  {len(module_map)}")
        print(f"Total Units:    {len(units_data)}")
        print()
        print("✓ Data successfully imported to NeonDB!")
        print()
        print("Next step: Sync to ChromaDB")
        print("  → uv run --env-file .env python scripts/load_units.py --force")

    except Exception as e:
        session.rollback()
        print(f"\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        session.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: import_json_to_neondb.py <json_path>")
        sys.exit(1)

    json_path = sys.argv[1]

    if not Path(json_path).exists():
        print(f"Error: {json_path} does not exist")
        sys.exit(1)

    import_json(json_path)


if __name__ == "__main__":
    main()
