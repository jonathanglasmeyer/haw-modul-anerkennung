#!/usr/bin/env python3
"""One-time migration script: Airtable → NeonDB.

Reads data from Airtable (or cache) and imports into NeonDB.
"""
import sys
import os
from typing import Dict, Set

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from matching.airtable_legacy import fetch_units_from_airtable
from matching.database import get_session
from matching.models import Person, Module, Unit
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError


def migrate():
    """Migrate all Units, Modules, and Personen from Airtable to NeonDB."""
    print("=== Airtable → NeonDB Migration ===\n")

    # Fetch from Airtable
    print("Fetching data from Airtable...")
    cache_dir = os.getenv("VECTORSTORE_PATH", "./data/vectorstore")
    data = fetch_units_from_airtable(cache_dir=cache_dir, force_refresh=False)

    units_data = data.get("units", {})
    modules_data = data.get("modules", {})

    print(f"Found {len(units_data)} units and {len(modules_data)} modules\n")

    if not units_data or not modules_data:
        print("No data to migrate!")
        return

    session = get_session()

    try:
        # Step 1: Migrate Personen
        print("Step 1: Migrating Personen...")
        personen_names: Set[str] = set()
        for unit in units_data.values():
            verantwortliche = unit.get("verantwortliche", [])
            personen_names.update(verantwortliche)

        personen_map: Dict[str, Person] = {}
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
                session.flush()  # Get ID immediately
                personen_map[name] = person
                personen_created += 1

        session.commit()
        print(f"  ✓ Created {personen_created} new personen")
        print(f"  ✓ Found {personen_existing} existing personen\n")

        # Step 2: Migrate Modules
        print("Step 2: Migrating Modules...")
        module_map: Dict[str, Module] = {}
        modules_created = 0
        modules_existing = 0

        for module_id, module_data in modules_data.items():
            # Check if exists
            existing = session.execute(
                select(Module).where(Module.module_id == module_id)
            ).scalar_one_or_none()

            if existing:
                module_map[module_id] = existing
                modules_existing += 1
            else:
                module = Module(
                    module_id=module_id,
                    title=module_data.get("title", ""),
                    credits=int(module_data["credits"]) if module_data.get("credits") else None,
                    sws=int(module_data["sws"]) if module_data.get("sws") else None,
                    semester=int(module_data["semester"]) if module_data.get("semester") else None,
                    lernziele=module_data.get("gesamtziele"),
                    pruefungsleistung=module_data.get("pruefungsleistung"),
                )
                session.add(module)
                session.flush()
                module_map[module_id] = module
                modules_created += 1

        session.commit()
        print(f"  ✓ Created {modules_created} new modules")
        print(f"  ✓ Found {modules_existing} existing modules\n")

        # Step 3: Migrate Units
        print("Step 3: Migrating Units...")
        units_created = 0
        units_existing = 0
        units_skipped = 0

        for unit_id, unit_data in units_data.items():
            # Check if exists
            existing = session.execute(
                select(Unit).where(Unit.unit_id == unit_id)
            ).scalar_one_or_none()

            if existing:
                units_existing += 1
                continue

            # Get module reference
            module_id = unit_data.get("module_id")
            if not module_id or module_id not in module_map:
                print(f"  ⚠ Skipping unit {unit_id}: missing module reference")
                units_skipped += 1
                continue

            module = module_map[module_id]

            # Create unit
            unit = Unit(
                unit_id=unit_id,
                title=unit_data.get("title", ""),
                module_id=module.id,
                semester=int(unit_data["semester"]) if unit_data.get("semester") else None,
                sws=int(unit_data["sws"]) if unit_data.get("sws") else None,
                workload=unit_data.get("workload"),
                lehrsprache=unit_data.get("lehrsprache"),
                lernziele=unit_data.get("learning_outcomes_text"),
                inhalte=unit_data.get("content"),
            )

            # Add verantwortliche relationships
            verantwortliche_names = unit_data.get("verantwortliche", [])
            for name in verantwortliche_names:
                if name in personen_map:
                    unit.verantwortliche.append(personen_map[name])

            session.add(unit)
            units_created += 1

        session.commit()
        print(f"  ✓ Created {units_created} new units")
        print(f"  ✓ Found {units_existing} existing units")
        if units_skipped > 0:
            print(f"  ⚠ Skipped {units_skipped} units (missing module reference)\n")
        else:
            print()

        # Summary
        print("=== Migration Complete ===")
        print(f"Total Personen: {len(personen_map)}")
        print(f"Total Modules:  {len(module_map)}")
        print(f"Total Units:    {units_created + units_existing}")
        print()
        print("✓ Data successfully migrated to NeonDB!")
        print()
        print("Next step: Run sync_from_database() to populate ChromaDB")
        print("  → uv run --env-file .env python scripts/load_units.py --force")

    except Exception as e:
        session.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    migrate()
