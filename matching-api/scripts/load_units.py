#!/usr/bin/env python3
"""Sync units from NeonDB into ChromaDB."""
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from matching.chromadb import sync_from_database


def main():
    persist_dir = os.getenv("VECTORSTORE_PATH", "./data/vectorstore")
    force = "--force" in sys.argv

    print(f"Syncing units to: {persist_dir}")
    if force:
        print("Force refresh enabled")

    count = sync_from_database(force_refresh=force)
    print(f"Done! {count} units in ChromaDB")


if __name__ == "__main__":
    main()
