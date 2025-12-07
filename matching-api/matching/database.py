"""Database client for NeonDB with CRUD operations."""
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session, sessionmaker, joinedload
from matching.models import Base, Unit, Module, Person


# Database engine and session factory
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session() -> Session:
    """Get a database session."""
    return SessionLocal()


def get_units_checksum() -> Optional[datetime]:
    """
    Get checksum representing current state of units table.

    Returns the max(updated_at) timestamp from units table.
    This is a fast query (milliseconds) to detect if data changed.
    """
    session = get_session()
    try:
        result = session.execute(
            select(func.max(Unit.updated_at))
        ).scalar()
        return result
    finally:
        session.close()


def fetch_units_from_db() -> Dict[str, Any]:
    """
    Fetch all units, modules, and personen from NeonDB.

    Returns dict in same format as airtable.py for compatibility with chromadb.py:
    {
        "units": {
            "unit_id": {
                "title": "...",
                "module_id": "...",
                "module_record_id": <int>,
                "semester": "...",
                ...
            }
        },
        "modules": {
            "module_id": {
                "title": "...",
                "credits": "...",
                ...
            }
        }
    }
    """
    session = get_session()
    try:
        # Fetch all modules
        modules_query = select(Module)
        modules = session.execute(modules_query).scalars().all()

        modules_dict = {}
        for m in modules:
            modules_dict[m.module_id] = {
                "airtable_id": str(m.id),  # For compatibility
                "title": m.title,
                "credits": str(m.credits) if m.credits else None,
                "sws": str(m.sws) if m.sws else None,
                "semester": str(m.semester) if m.semester else None,
                "gesamtziele": m.lernziele or "",
                "pruefungsleistung": m.pruefungsleistung or "",
            }

        # Fetch all units with relationships
        units_query = select(Unit).options(
            joinedload(Unit.module),
            joinedload(Unit.verantwortliche)
        )
        units = session.execute(units_query).unique().scalars().all()

        units_dict = {}
        for u in units:
            verantwortliche_names = [p.name for p in u.verantwortliche]

            units_dict[u.unit_id] = {
                "airtable_id": str(u.id),  # For compatibility
                "title": u.title,
                "module_id": u.module.module_id,
                "module_record_id": str(u.module.id),
                "semester": str(u.semester) if u.semester else None,
                "sws": str(u.sws) if u.sws else None,
                "workload": u.workload,
                "lehrsprache": u.lehrsprache,
                "learning_outcomes_text": u.lernziele or "",
                "content": u.inhalte or "",
                "verantwortliche": verantwortliche_names,
            }

        return {
            "units": units_dict,
            "modules": modules_dict,
        }

    finally:
        session.close()


# ===== CRUD for Units =====

def get_all_units(session: Session) -> List[Unit]:
    """Get all units with relationships."""
    query = select(Unit).options(
        joinedload(Unit.module),
        joinedload(Unit.verantwortliche)
    )
    return list(session.execute(query).unique().scalars().all())


def get_unit_by_id(session: Session, unit_id: int) -> Optional[Unit]:
    """Get a unit by ID."""
    query = select(Unit).where(Unit.id == unit_id).options(
        joinedload(Unit.module),
        joinedload(Unit.verantwortliche)
    )
    return session.execute(query).unique().scalar_one_or_none()


def create_unit(session: Session, data: Dict[str, Any]) -> Unit:
    """Create a new unit."""
    # Extract verantwortliche IDs if provided
    verantwortliche_ids = data.pop("verantwortliche_ids", [])

    # Create unit
    unit = Unit(**data)

    # Add verantwortliche relationships
    if verantwortliche_ids:
        persons = session.execute(
            select(Person).where(Person.id.in_(verantwortliche_ids))
        ).scalars().all()
        unit.verantwortliche = list(persons)

    session.add(unit)
    session.commit()
    session.refresh(unit)
    return unit


def update_unit(session: Session, unit_id: int, data: Dict[str, Any]) -> Optional[Unit]:
    """Update a unit."""
    unit = get_unit_by_id(session, unit_id)
    if not unit:
        return None

    # Extract verantwortliche IDs if provided
    verantwortliche_ids = data.pop("verantwortliche_ids", None)

    # Update fields
    for key, value in data.items():
        if hasattr(unit, key):
            setattr(unit, key, value)

    # Update verantwortliche relationships if provided
    if verantwortliche_ids is not None:
        persons = session.execute(
            select(Person).where(Person.id.in_(verantwortliche_ids))
        ).scalars().all()
        unit.verantwortliche = list(persons)

    session.commit()
    session.refresh(unit)
    return unit


def delete_unit(session: Session, unit_id: int) -> bool:
    """Delete a unit."""
    unit = get_unit_by_id(session, unit_id)
    if not unit:
        return False

    session.delete(unit)
    session.commit()
    return True


# ===== CRUD for Modules =====

def get_all_modules(session: Session) -> List[Module]:
    """Get all modules."""
    return list(session.execute(select(Module)).scalars().all())


def get_module_by_id(session: Session, module_id: int) -> Optional[Module]:
    """Get a module by ID."""
    return session.execute(
        select(Module).where(Module.id == module_id)
    ).scalar_one_or_none()


def create_module(session: Session, data: Dict[str, Any]) -> Module:
    """Create a new module."""
    module = Module(**data)
    session.add(module)
    session.commit()
    session.refresh(module)
    return module


def update_module(session: Session, module_id: int, data: Dict[str, Any]) -> Optional[Module]:
    """Update a module."""
    module = get_module_by_id(session, module_id)
    if not module:
        return None

    for key, value in data.items():
        if hasattr(module, key):
            setattr(module, key, value)

    session.commit()
    session.refresh(module)
    return module


def delete_module(session: Session, module_id: int) -> bool:
    """Delete a module."""
    module = get_module_by_id(session, module_id)
    if not module:
        return False

    session.delete(module)
    session.commit()
    return True


# ===== CRUD for Personen =====

def get_all_personen(session: Session) -> List[Person]:
    """Get all personen."""
    return list(session.execute(select(Person)).scalars().all())


def get_person_by_id(session: Session, person_id: int) -> Optional[Person]:
    """Get a person by ID."""
    return session.execute(
        select(Person).where(Person.id == person_id)
    ).scalar_one_or_none()


def create_person(session: Session, data: Dict[str, Any]) -> Person:
    """Create a new person."""
    person = Person(**data)
    session.add(person)
    session.commit()
    session.refresh(person)
    return person


def update_person(session: Session, person_id: int, data: Dict[str, Any]) -> Optional[Person]:
    """Update a person."""
    person = get_person_by_id(session, person_id)
    if not person:
        return None

    for key, value in data.items():
        if hasattr(person, key):
            setattr(person, key, value)

    session.commit()
    session.refresh(person)
    return person


def delete_person(session: Session, person_id: int) -> bool:
    """Delete a person."""
    person = get_person_by_id(session, person_id)
    if not person:
        return False

    session.delete(person)
    session.commit()
    return True
