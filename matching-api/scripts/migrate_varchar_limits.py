#!/usr/bin/env python3
"""Migrate workload and lehrsprache columns from VARCHAR(50) to VARCHAR(255)."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from matching.database import get_session
from sqlalchemy import text

def migrate():
    """Run ALTER TABLE to increase column sizes."""
    session = get_session()

    try:
        print("Altering units table columns...")

        # Alter workload column
        session.execute(text("""
            ALTER TABLE units
            ALTER COLUMN workload TYPE VARCHAR(255)
        """))

        # Alter lehrsprache column
        session.execute(text("""
            ALTER TABLE units
            ALTER COLUMN lehrsprache TYPE VARCHAR(255)
        """))

        session.commit()
        print("✓ Successfully migrated columns to VARCHAR(255)")

    except Exception as e:
        session.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    migrate()
