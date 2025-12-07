"""Pytest fixtures for testing admin API."""
import os
import tempfile

# Set test environment variables BEFORE any imports
os.environ["ADMIN_PASSWORD"] = "test-password"
# Use a temporary file instead of :memory: to avoid threading issues
_test_db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_file.name}"
os.environ["GEMINI_API_KEY"] = "test-key"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from fastapi.testclient import TestClient

from matching.models import Base, Unit, Module, Person
from matching.auth import create_session
from matching import database


# App will be imported in client fixture after patching database


@pytest.fixture(scope="function", autouse=True)
def test_db_engine():
    """Create tables in the test database before each test."""
    # Use the same DATABASE_URL that's already set in environment
    from matching import database
    Base.metadata.drop_all(bind=database.engine)
    Base.metadata.create_all(bind=database.engine)
    yield database.engine
    Base.metadata.drop_all(bind=database.engine)


@pytest.fixture(scope="function")
def db_session(test_db_engine):
    """Create a new database session for a test."""
    SessionLocal = sessionmaker(bind=test_db_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def sample_personen(db_session):
    """Create sample persons for testing."""
    persons = [
        Person(name="Prof. Dr. Schmidt"),
        Person(name="Prof. Dr. Müller"),
        Person(name="Dr. Weber"),
    ]
    for person in persons:
        db_session.add(person)
    db_session.commit()
    for person in persons:
        db_session.refresh(person)
    return persons


@pytest.fixture(scope="function")
def sample_modules(db_session):
    """Create sample modules for testing."""
    modules = [
        Module(
            module_id="TEST_M1",
            title="Test Module 1",
            credits=6,
            sws=4,
            semester=5,
            lernziele="Test learning objectives",
            pruefungsleistung="Test exam",
        ),
        Module(
            module_id="TEST_M2",
            title="Test Module 2",
            credits=3,
            sws=2,
            semester=3,
        ),
    ]
    for module in modules:
        db_session.add(module)
    db_session.commit()
    for module in modules:
        db_session.refresh(module)
    return modules


@pytest.fixture(scope="function")
def sample_units(db_session, sample_modules, sample_personen):
    """Create sample units for testing."""
    units = [
        Unit(
            unit_id="TEST_M1_U1",
            title="Test Unit 1",
            module_id=sample_modules[0].id,
            semester=5,
            sws=2,
            lernziele="Test objectives 1",
        ),
        Unit(
            unit_id="TEST_M1_U2",
            title="Test Unit 2",
            module_id=sample_modules[0].id,
            semester=5,
            sws=2,
        ),
        Unit(
            unit_id="TEST_M2_U1",
            title="Test Unit 3",
            module_id=sample_modules[1].id,
            semester=3,
            sws=2,
        ),
    ]

    # Assign verantwortliche to first unit
    units[0].verantwortliche = [sample_personen[0], sample_personen[1]]

    for unit in units:
        db_session.add(unit)
    db_session.commit()
    for unit in units:
        db_session.refresh(unit)
    return units


@pytest.fixture(scope="function")
def admin_token():
    """Create a valid admin session token."""
    return create_session()


@pytest.fixture(scope="function")
def client():
    """Create a test client for the FastAPI app with test database."""
    from app import app
    return TestClient(app)


@pytest.fixture(scope="function")
def auth_headers(admin_token):
    """Create authorization headers with valid token."""
    return {"authorization": admin_token}


@pytest.fixture(autouse=True)
def set_test_env(monkeypatch):
    """Set test environment variables."""
    monkeypatch.setenv("ADMIN_PASSWORD", "test-password")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
