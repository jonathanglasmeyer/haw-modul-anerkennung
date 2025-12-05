#!/usr/bin/env python3
"""Import Excel data to Airtable via mcporter."""
import subprocess
import json
import os
from datetime import datetime

import openpyxl

# Load Excel
wb = openpyxl.load_workbook('data/kern/uebersichten/antraege-tracking.xlsx', data_only=True)
ws = wb.active

# Parse rows (skip header)
rows = list(ws.iter_rows(min_row=2, max_row=61, values_only=True))

# Group by Antrags-Nr to create unique Anträge
antraege = {}
teilantraege_data = []

for row in rows:
    if not row[1]:  # Skip empty Antrags-Nr
        continue

    antrags_nr = row[1]

    # Create/update Antrag entry
    if antrags_nr not in antraege:
        antrag_datum = row[5]
        if isinstance(antrag_datum, datetime):
            antrag_datum = antrag_datum.strftime('%Y-%m-%d')

        antraege[antrags_nr] = {
            'Antrags-Nr': antrags_nr,
            'Name': row[2] if row[2] else '',
            'Matrikel': str(row[3]) if row[3] else '',
            'Email': row[4] if row[4] else '',
            'Antragsdatum': antrag_datum,
            'Hochschule': row[13] if row[13] else '',
            'Prio': row[6] if row[6] else 'normal',
        }
        # Add Bescheid dates if present
        if row[19]:
            bescheid_erstellt = row[19]
            if isinstance(bescheid_erstellt, datetime):
                antraege[antrags_nr]['Bescheid erstellt'] = bescheid_erstellt.strftime('%Y-%m-%d')
        if row[20]:
            bescheid_versandt = row[20]
            if isinstance(bescheid_versandt, datetime):
                antraege[antrags_nr]['Bescheid versandt am'] = bescheid_versandt.strftime('%Y-%m-%d')

    # Collect Teilantrag data
    teilantrag = {
        'antrags_nr': antrags_nr,
        'Teilantrag-ID': row[7] if row[7] else '',
        'Ziel-Modul': str(row[8]) if row[8] else '',
        'Ziel-Unit': str(row[9]) if row[9] else '',
        'Note': str(row[11]) if row[11] else '',
        'Prozentpunkte': float(row[12]) if row[12] and not str(row[12]).startswith('#') else None,
        'Verantwortlicher': row[14] if row[14] else '',
        'Angefragt von': row[15] if row[15] else '',
        'Zwischenstand': row[16] if row[16] else '',
        'Begründung': row[18] if row[18] else '',
    }

    # Map Status
    status_raw = row[10] if row[10] else ''
    status_map = {
        '3 - Nachfragen bei Modulverantwortlichen': '3 - Nachfragen bei Modulverantwortlichen',
        '3 - Nachfragen bei Modulverantwortlichen ': '3 - Nachfragen bei Modulverantwortlichen',
        '4 - Nachfragen bei Modulverantwortlichen': '4 - Antwort fehlt',
        '4 - Antwort von Modulverantw. fehlt': '4 - Antwort fehlt',
        '5 - Antwort von Modulverantw. erhalten': '5 - Antwort erhalten',
        '6 - Antwort von Modulverantw. erhalten': '5 - Antwort erhalten',
        '6 - alle Antworten erhalten': '6 - alle Antworten erhalten',
        '7 - Bescheid versandt': '7 - Bescheid versandt',
    }
    teilantrag['Status'] = status_map.get(status_raw, '')

    # Map Stellungnahme
    stellungnahme_raw = row[17] if row[17] else ''
    if stellungnahme_raw.lower() in ['positiv', 'negativ', 'offen']:
        teilantrag['Stellungnahme'] = stellungnahme_raw.lower()

    teilantraege_data.append(teilantrag)

print(f"Found {len(antraege)} Anträge and {len(teilantraege_data)} Teilanträge")

# Helper to call mcporter
def mcporter_call(tool, **kwargs):
    cmd = f"source .env && AIRTABLE_API_KEY=\"$AIRTABLE_API_KEY\" mcporter airtable.{tool}"
    for k, v in kwargs.items():
        if isinstance(v, dict):
            cmd += f" {k}='{json.dumps(v)}'"
        else:
            cmd += f" {k}={v}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd='/Users/jonathan.glasmeyer/Projects/stephan-uni')
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return None
    return json.loads(result.stdout) if result.stdout.strip() else None

BASE_ID = 'appoawrI73padNkWy'
ANTRAEGE_TABLE = 'tbl9cc01xSjzI6lat'
TEILANTRAEGE_TABLE = 'tblsylFyYJyka43XT'

# Create Anträge and store their record IDs
antrag_record_ids = {}
for antrags_nr, antrag in antraege.items():
    fields = {k: v for k, v in antrag.items() if v}  # Remove empty fields
    print(f"Creating Antrag {antrags_nr}...")

    cmd = f'''source .env && AIRTABLE_API_KEY="$AIRTABLE_API_KEY" npx mcporter --config ~/.config/mcporter.json airtable.create_record baseId={BASE_ID} tableId={ANTRAEGE_TABLE} fields='{json.dumps(fields)}' '''
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd='/Users/jonathan.glasmeyer/Projects/stephan-uni')
    if result.returncode == 0 and result.stdout.strip():
        record = json.loads(result.stdout)
        antrag_record_ids[antrags_nr] = record['id']
        print(f"  -> {record['id']}")
    else:
        print(f"  Error: {result.stderr}")

print(f"\nCreated {len(antrag_record_ids)} Anträge records")

# Create Teilanträge with links to parent Antrag
for ta in teilantraege_data:
    antrags_nr = ta.pop('antrags_nr')
    if antrags_nr not in antrag_record_ids:
        print(f"Skipping Teilantrag - no parent Antrag found for {antrags_nr}")
        continue

    # Add link to parent Antrag
    ta['Antrag'] = [antrag_record_ids[antrags_nr]]

    # Remove empty fields and None values
    fields = {k: v for k, v in ta.items() if v is not None and v != ''}

    print(f"Creating Teilantrag {ta.get('Teilantrag-ID', '?')} for {antrags_nr}...")

    cmd = f'''source .env && AIRTABLE_API_KEY="$AIRTABLE_API_KEY" npx mcporter --config ~/.config/mcporter.json airtable.create_record baseId={BASE_ID} tableId={TEILANTRAEGE_TABLE} fields='{json.dumps(fields)}' '''
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd='/Users/jonathan.glasmeyer/Projects/stephan-uni')
    if result.returncode == 0 and result.stdout.strip():
        record = json.loads(result.stdout)
        print(f"  -> {record['id']}")
    else:
        print(f"  Error: {result.stderr}")

print("\nDone!")
