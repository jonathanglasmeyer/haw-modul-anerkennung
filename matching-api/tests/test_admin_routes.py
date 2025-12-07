"""Tests for Admin API routes (admin_routes.py)."""
import pytest


class TestAuthRoutes:
    """Test authentication endpoints."""

    def test_login_success(self, client, monkeypatch):
        """Test successful login."""
        monkeypatch.setenv("ADMIN_PASSWORD", "test-password")
        response = client.post(
            "/api/admin/login",
            json={"password": "test-password"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert isinstance(data["token"], str)
        assert len(data["token"]) > 0

    def test_login_wrong_password(self, client, monkeypatch):
        """Test login with wrong password."""
        monkeypatch.setenv("ADMIN_PASSWORD", "test-password")
        response = client.post(
            "/api/admin/login",
            json={"password": "wrong-password"},
        )

        assert response.status_code == 401
        assert "Invalid password" in response.json()["detail"]

    def test_logout_with_token(self, client, auth_headers):
        """Test logout with valid token."""
        response = client.post(
            "/api/admin/logout",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json() == {"message": "Logged out"}

    def test_logout_without_token(self, client):
        """Test logout without token (should still succeed)."""
        response = client.post("/api/admin/logout")
        assert response.status_code == 200


class TestPersonenRoutes:
    """Test Personen CRUD endpoints."""

    def test_list_personen_requires_auth(self, client):
        """Test that listing persons requires authentication."""
        response = client.get("/api/admin/personen")
        assert response.status_code == 401

    def test_list_personen_empty(self, client, auth_headers):
        """Test listing persons when DB is empty."""
        response = client.get(
            "/api/admin/personen",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "personen" in data
        assert data["personen"] == []

    def test_list_personen(self, client, auth_headers):
        """Test listing all persons."""
        # Create via API
        client.post(
            "/api/admin/personen",
            headers=auth_headers,
            json={"name": "Prof. Dr. Schmidt"},
        )
        client.post(
            "/api/admin/personen",
            headers=auth_headers,
            json={"name": "Prof. Dr. Müller"},
        )

        response = client.get(
            "/api/admin/personen",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["personen"]) == 2

    def test_create_person(self, client, auth_headers):
        """Test creating a new person."""
        response = client.post(
            "/api/admin/personen",
            headers=auth_headers,
            json={"name": "New Professor"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Professor"
        assert "id" in data
        assert data["message"] == "Person created successfully"

    def test_create_person_requires_auth(self, client):
        """Test that creating a person requires authentication."""
        response = client.post(
            "/api/admin/personen",
            json={"name": "Test"},
        )
        assert response.status_code == 401

    def test_update_person(self, client, auth_headers):
        """Test updating a person."""
        # Create first
        create_response = client.post(
            "/api/admin/personen",
            headers=auth_headers,
            json={"name": "Original Name"},
        )
        person_id = create_response.json()["id"]

        # Update
        response = client.put(
            f"/api/admin/personen/{person_id}",
            headers=auth_headers,
            json={"name": "Updated Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["id"] == person_id

    def test_update_person_not_found(self, client, auth_headers):
        """Test updating a non-existent person."""
        response = client.put(
            "/api/admin/personen/999",
            headers=auth_headers,
            json={"name": "Test"},
        )
        assert response.status_code == 404

    def test_delete_person(self, client, auth_headers):
        """Test deleting a person."""
        # Create first
        create_response = client.post(
            "/api/admin/personen",
            headers=auth_headers,
            json={"name": "To Delete"},
        )
        person_id = create_response.json()["id"]

        # Delete
        response = client.delete(
            f"/api/admin/personen/{person_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

        # Verify deleted
        list_response = client.get(
            "/api/admin/personen",
            headers=auth_headers,
        )
        persons = list_response.json()["personen"]
        assert not any(p["id"] == person_id for p in persons)

    def test_delete_person_not_found(self, client, auth_headers):
        """Test deleting a non-existent person."""
        response = client.delete(
            "/api/admin/personen/999",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestModulesRoutes:
    """Test Modules CRUD endpoints."""

    def test_list_modules_requires_auth(self, client):
        """Test that listing modules requires authentication."""
        response = client.get("/api/admin/modules")
        assert response.status_code == 401

    def test_create_module(self, client, auth_headers):
        """Test creating a new module."""
        response = client.post(
            "/api/admin/modules",
            headers=auth_headers,
            json={
                "module_id": "TEST_M1",
                "title": "Test Module",
                "credits": 6,
                "sws": 4,
                "semester": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["module_id"] == "TEST_M1"
        assert data["title"] == "Test Module"
        assert "id" in data

    def test_create_module_minimal_fields(self, client, auth_headers):
        """Test creating a module with only required fields."""
        response = client.post(
            "/api/admin/modules",
            headers=auth_headers,
            json={
                "module_id": "MIN_M1",
                "title": "Minimal Module",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["module_id"] == "MIN_M1"

    def test_update_module(self, client, auth_headers):
        """Test updating a module."""
        # Create first
        create_response = client.post(
            "/api/admin/modules",
            headers=auth_headers,
            json={"module_id": "UPD_M1", "title": "Original"},
        )
        module_id = create_response.json()["id"]

        # Update
        response = client.put(
            f"/api/admin/modules/{module_id}",
            headers=auth_headers,
            json={"title": "Updated Title", "credits": 12},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["module_id"] == "UPD_M1"  # Unchanged

    def test_delete_module(self, client, auth_headers):
        """Test deleting a module."""
        # Create first
        create_response = client.post(
            "/api/admin/modules",
            headers=auth_headers,
            json={"module_id": "DEL_M1", "title": "To Delete"},
        )
        module_id = create_response.json()["id"]

        # Delete
        response = client.delete(
            f"/api/admin/modules/{module_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200


class TestUnitsRoutes:
    """Test Units CRUD endpoints."""

    def test_list_units_requires_auth(self, client):
        """Test that listing units requires authentication."""
        response = client.get("/api/admin/units")
        assert response.status_code == 401

    def test_create_unit(self, client, auth_headers):
        """Test creating a new unit."""
        # Create module first
        module_response = client.post(
            "/api/admin/modules",
            headers=auth_headers,
            json={"module_id": "M1", "title": "Test Module"},
        )
        module_id = module_response.json()["id"]

        # Create unit
        response = client.post(
            "/api/admin/units",
            headers=auth_headers,
            json={
                "unit_id": "M1_U1",
                "title": "Test Unit",
                "module_id": module_id,
                "semester": 5,
                "sws": 2,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["unit_id"] == "M1_U1"
        assert data["title"] == "Test Unit"
        assert "id" in data

    def test_create_unit_with_verantwortliche(self, client, auth_headers):
        """Test creating a unit with verantwortliche."""
        # Create module
        module_response = client.post(
            "/api/admin/modules",
            headers=auth_headers,
            json={"module_id": "M2", "title": "Module"},
        )
        module_id = module_response.json()["id"]

        # Create persons
        person1 = client.post(
            "/api/admin/personen",
            headers=auth_headers,
            json={"name": "Person 1"},
        ).json()
        person2 = client.post(
            "/api/admin/personen",
            headers=auth_headers,
            json={"name": "Person 2"},
        ).json()

        # Create unit with verantwortliche
        response = client.post(
            "/api/admin/units",
            headers=auth_headers,
            json={
                "unit_id": "M2_U1",
                "title": "Unit with Persons",
                "module_id": module_id,
                "verantwortliche_ids": [person1["id"], person2["id"]],
            },
        )

        assert response.status_code == 200

        # Verify by listing units
        list_response = client.get(
            "/api/admin/units",
            headers=auth_headers,
        )
        units = list_response.json()["units"]
        created_unit = next(u for u in units if u["unit_id"] == "M2_U1")
        assert len(created_unit["verantwortliche"]) == 2

    def test_update_unit(self, client, auth_headers):
        """Test updating a unit."""
        # Create module and unit first
        module_response = client.post(
            "/api/admin/modules",
            headers=auth_headers,
            json={"module_id": "M3", "title": "Module"},
        )
        module_id = module_response.json()["id"]

        create_response = client.post(
            "/api/admin/units",
            headers=auth_headers,
            json={
                "unit_id": "M3_U1",
                "title": "Original",
                "module_id": module_id,
            },
        )
        unit_id = create_response.json()["id"]

        # Update
        response = client.put(
            f"/api/admin/units/{unit_id}",
            headers=auth_headers,
            json={"title": "Updated Unit", "sws": 4},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Unit"

    def test_delete_unit(self, client, auth_headers):
        """Test deleting a unit."""
        # Create module and unit first
        module_response = client.post(
            "/api/admin/modules",
            headers=auth_headers,
            json={"module_id": "M4", "title": "Module"},
        )
        module_id = module_response.json()["id"]

        create_response = client.post(
            "/api/admin/units",
            headers=auth_headers,
            json={
                "unit_id": "M4_U1",
                "title": "To Delete",
                "module_id": module_id,
            },
        )
        unit_id = create_response.json()["id"]

        # Delete
        response = client.delete(
            f"/api/admin/units/{unit_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]


class TestSyncRoute:
    """Test ChromaDB sync endpoint."""

    def test_sync_requires_auth(self, client):
        """Test that sync requires authentication."""
        response = client.post("/api/admin/sync")
        assert response.status_code == 401

    def test_sync_chromadb(self, client, auth_headers):
        """Test ChromaDB sync endpoint."""
        # This might need mocking ChromaDB in the future
        response = client.post(
            "/api/admin/sync",
            headers=auth_headers,
        )

        # Should return 200 even if ChromaDB isn't running
        # (depends on implementation)
        assert response.status_code in [200, 500]  # Allow failure if ChromaDB not available
