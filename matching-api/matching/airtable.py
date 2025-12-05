"""Airtable client for fetching units and modules."""
import os
import json
import httpx
from datetime import datetime
from pathlib import Path


AIRTABLE_BASE_ID = "appoawrI73padNkWy"
UNITS_TABLE = "tblbUxQbNAkGRxdT0"  # Unit table ID
MODULES_TABLE = "tblNwW2NWEnSdnyzM"  # Module table ID
CACHE_FILE = "airtable_cache.json"


def get_headers():
    """Get Airtable API headers."""
    api_key = os.environ.get("AIRTABLE_API_KEY")
    if not api_key:
        raise ValueError("AIRTABLE_API_KEY environment variable required")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }


def fetch_all_records(table_name: str) -> list[dict]:
    """Fetch all records from an Airtable table with pagination."""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table_name}"
    headers = get_headers()

    records = []
    offset = None

    while True:
        params = {"pageSize": 100}
        if offset:
            params["offset"] = offset

        response = httpx.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        records.extend(data.get("records", []))
        offset = data.get("offset")

        if not offset:
            break

    return records


def get_latest_modified(records: list[dict]) -> str | None:
    """Get the latest 'Last Modified' timestamp from records."""
    latest = None
    for record in records:
        modified = record.get("fields", {}).get("Last Modified")
        if modified:
            if latest is None or modified > latest:
                latest = modified
    return latest


def load_cache(cache_dir: str) -> dict | None:
    """Load cached data if exists."""
    cache_path = Path(cache_dir) / CACHE_FILE
    if cache_path.exists():
        with open(cache_path, "r") as f:
            return json.load(f)
    return None


def save_cache(cache_dir: str, data: dict):
    """Save data to cache."""
    cache_path = Path(cache_dir) / CACHE_FILE
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(data, f, indent=2)


def fetch_units_from_airtable(cache_dir: str = "./data", force_refresh: bool = False) -> dict:
    """Fetch units and modules from Airtable, using cache if unchanged.

    Args:
        cache_dir: Directory for cache file
        force_refresh: Force fetch even if cache is fresh

    Returns:
        Dict with 'units' and 'modules' keyed by ID
    """
    cache = load_cache(cache_dir)

    # Fetch units to check for updates
    print("Checking Airtable for updates...")
    unit_records = fetch_all_records(UNITS_TABLE)
    latest_unit_modified = get_latest_modified(unit_records)

    # Check if cache is still valid
    if not force_refresh and cache:
        cached_modified = cache.get("last_modified")
        if cached_modified and latest_unit_modified and cached_modified >= latest_unit_modified:
            print(f"Cache is fresh (last modified: {cached_modified})")
            return {
                "units": cache.get("units", {}),
                "modules": cache.get("modules", {})
            }

    print(f"Fetching fresh data from Airtable...")

    # Fetch modules
    module_records = fetch_all_records(MODULES_TABLE)

    # Build module lookup by Airtable record ID
    module_by_record_id = {}
    modules = {}
    for record in module_records:
        fields = record.get("fields", {})
        module_id = fields.get("Modul-ID")
        if module_id:
            module_by_record_id[record["id"]] = module_id
            modules[module_id] = {
                "airtable_id": record["id"],
                "title": fields.get("Titel", ""),
                "credits": fields.get("Credits", ""),
                "sws": fields.get("SWS", ""),
                "semester": fields.get("Semester", ""),
                "gesamtziele": fields.get("Lernziele", ""),
                "pruefungsleistung": fields.get("Prüfungsform", ""),
            }

    # Convert units
    units = {}
    for record in unit_records:
        fields = record.get("fields", {})
        unit_id = fields.get("Unit-ID")
        if unit_id:
            # Get linked module ID via record ID lookup
            module_links = fields.get("Modul", [])
            module_record_id = module_links[0] if module_links else None
            module_id = module_by_record_id.get(module_record_id, "")

            units[unit_id] = {
                "airtable_id": record["id"],
                "title": fields.get("Titel", ""),
                "module_id": module_id,
                "module_record_id": module_record_id,
                "semester": fields.get("Semester", ""),
                "sws": fields.get("SWS", ""),
                "workload": fields.get("Workload", ""),
                "lehrsprache": fields.get("Lehrsprache", ""),
                "learning_outcomes_text": fields.get("Lernziele", ""),
                "content": fields.get("Inhalte", ""),
            }

    # Save to cache
    cache_data = {
        "last_modified": latest_unit_modified or datetime.now().isoformat(),
        "fetched_at": datetime.now().isoformat(),
        "units": units,
        "modules": modules
    }
    save_cache(cache_dir, cache_data)

    print(f"Fetched {len(units)} units and {len(modules)} modules from Airtable")

    return {"units": units, "modules": modules}
