"""Tests for database operations (database.py)."""
import pytest
from matching.database import (
    get_all_units,
    get_unit_by_id,
    create_unit,
    update_unit,
    delete_unit,
    get_all_modules,
    get_module_by_id,
    create_module,
    update_module,
    delete_module,
    get_all_personen,
    get_person_by_id,
    create_person,
    update_person,
    delete_person,
)


class TestPersonCRUD:
    """Test Person CRUD operations."""

    def test_get_all_personen_empty(self, db_session):
        """Test getting all persons when DB is empty."""
        persons = get_all_personen(db_session)
        assert persons == []

    def test_get_all_personen(self, db_session, sample_personen):
        """Test getting all persons."""
        persons = get_all_personen(db_session)
        assert len(persons) == 3
        assert persons[0].name == "Prof. Dr. Schmidt"

    def test_get_person_by_id(self, db_session, sample_personen):
        """Test getting a person by ID."""
        person = get_person_by_id(db_session, sample_personen[0].id)
        assert person is not None
        assert person.name == "Prof. Dr. Schmidt"

    def test_get_person_by_id_not_found(self, db_session):
        """Test getting a non-existent person."""
        person = get_person_by_id(db_session, 999)
        assert person is None

    def test_create_person(self, db_session):
        """Test creating a new person."""
        data = {"name": "New Professor"}
        person = create_person(db_session, data)

        assert person.id is not None
        assert person.name == "New Professor"
        assert person.created_at is not None

    def test_update_person(self, db_session, sample_personen):
        """Test updating a person."""
        person = sample_personen[0]
        data = {"name": "Updated Name"}

        updated = update_person(db_session, person.id, data)
        assert updated.name == "Updated Name"
        assert updated.id == person.id

    def test_update_person_not_found(self, db_session):
        """Test updating a non-existent person."""
        result = update_person(db_session, 999, {"name": "Test"})
        assert result is None

    def test_delete_person(self, db_session, sample_personen):
        """Test deleting a person."""
        person_id = sample_personen[0].id
        result = delete_person(db_session, person_id)

        assert result is True
        assert get_person_by_id(db_session, person_id) is None

    def test_delete_person_not_found(self, db_session):
        """Test deleting a non-existent person."""
        result = delete_person(db_session, 999)
        assert result is False


class TestModuleCRUD:
    """Test Module CRUD operations."""

    def test_get_all_modules_empty(self, db_session):
        """Test getting all modules when DB is empty."""
        modules = get_all_modules(db_session)
        assert modules == []

    def test_get_all_modules(self, db_session, sample_modules):
        """Test getting all modules."""
        modules = get_all_modules(db_session)
        assert len(modules) == 2
        assert modules[0].module_id == "TEST_M1"

    def test_get_module_by_id(self, db_session, sample_modules):
        """Test getting a module by ID."""
        module = get_module_by_id(db_session, sample_modules[0].id)
        assert module is not None
        assert module.title == "Test Module 1"

    def test_create_module(self, db_session):
        """Test creating a new module."""
        data = {
            "module_id": "NEW_M1",
            "title": "New Module",
            "credits": 6,
            "sws": 4,
            "semester": 5,
        }
        module = create_module(db_session, data)

        assert module.id is not None
        assert module.module_id == "NEW_M1"
        assert module.title == "New Module"

    def test_update_module(self, db_session, sample_modules):
        """Test updating a module."""
        module = sample_modules[0]
        data = {"title": "Updated Title", "credits": 12}

        updated = update_module(db_session, module.id, data)
        assert updated.title == "Updated Title"
        assert updated.credits == 12
        assert updated.module_id == "TEST_M1"  # Unchanged

    def test_delete_module(self, db_session, sample_modules):
        """Test deleting a module."""
        module_id = sample_modules[0].id
        result = delete_module(db_session, module_id)

        assert result is True
        assert get_module_by_id(db_session, module_id) is None


class TestUnitCRUD:
    """Test Unit CRUD operations."""

    def test_get_all_units_empty(self, db_session):
        """Test getting all units when DB is empty."""
        units = get_all_units(db_session)
        assert units == []

    def test_get_all_units(self, db_session, sample_units):
        """Test getting all units with relationships."""
        units = get_all_units(db_session)
        assert len(units) == 3

        # Check relationships are loaded
        assert units[0].module is not None
        assert units[0].module.title == "Test Module 1"
        assert len(units[0].verantwortliche) == 2

    def test_get_unit_by_id(self, db_session, sample_units):
        """Test getting a unit by ID."""
        unit = get_unit_by_id(db_session, sample_units[0].id)
        assert unit is not None
        assert unit.title == "Test Unit 1"
        assert unit.module is not None
        assert len(unit.verantwortliche) == 2

    def test_create_unit_without_verantwortliche(self, db_session, sample_modules):
        """Test creating a unit without verantwortliche."""
        data = {
            "unit_id": "NEW_U1",
            "title": "New Unit",
            "module_id": sample_modules[0].id,
            "semester": 5,
            "sws": 2,
        }
        unit = create_unit(db_session, data)

        assert unit.id is not None
        assert unit.unit_id == "NEW_U1"
        assert unit.module_id == sample_modules[0].id
        assert len(unit.verantwortliche) == 0

    def test_create_unit_with_verantwortliche(self, db_session, sample_modules, sample_personen):
        """Test creating a unit with verantwortliche."""
        data = {
            "unit_id": "NEW_U2",
            "title": "New Unit with Persons",
            "module_id": sample_modules[0].id,
            "verantwortliche_ids": [sample_personen[0].id, sample_personen[1].id],
        }
        unit = create_unit(db_session, data)

        assert unit.id is not None
        assert len(unit.verantwortliche) == 2
        assert unit.verantwortliche[0].name == "Prof. Dr. Schmidt"

    def test_update_unit_basic_fields(self, db_session, sample_units):
        """Test updating unit basic fields."""
        unit = sample_units[0]
        data = {
            "title": "Updated Title",
            "sws": 4,
            "lernziele": "Updated objectives",
        }

        updated = update_unit(db_session, unit.id, data)
        assert updated.title == "Updated Title"
        assert updated.sws == 4
        assert updated.lernziele == "Updated objectives"
        assert updated.unit_id == "TEST_M1_U1"  # Unchanged

    def test_update_unit_verantwortliche(self, db_session, sample_units, sample_personen):
        """Test updating unit verantwortliche."""
        unit = sample_units[1]  # Unit without verantwortliche
        assert len(unit.verantwortliche) == 0

        data = {"verantwortliche_ids": [sample_personen[0].id]}
        updated = update_unit(db_session, unit.id, data)

        assert len(updated.verantwortliche) == 1
        assert updated.verantwortliche[0].name == "Prof. Dr. Schmidt"

    def test_update_unit_clear_verantwortliche(self, db_session, sample_units):
        """Test clearing unit verantwortliche."""
        unit = sample_units[0]  # Unit with verantwortliche
        assert len(unit.verantwortliche) == 2

        data = {"verantwortliche_ids": []}
        updated = update_unit(db_session, unit.id, data)

        assert len(updated.verantwortliche) == 0

    def test_delete_unit(self, db_session, sample_units):
        """Test deleting a unit."""
        unit_id = sample_units[0].id
        result = delete_unit(db_session, unit_id)

        assert result is True
        assert get_unit_by_id(db_session, unit_id) is None

    def test_delete_unit_not_found(self, db_session):
        """Test deleting a non-existent unit."""
        result = delete_unit(db_session, 999)
        assert result is False
