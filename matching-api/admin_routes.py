"""Admin API endpoints for managing Units, Modules, and Personen."""
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from matching.auth import verify_admin_password, create_session, verify_session, delete_session
from matching.database import (
    get_session,
    get_all_units, get_unit_by_id, create_unit, update_unit, delete_unit,
    get_all_modules, get_module_by_id, create_module, update_module, delete_module,
    get_all_personen, get_person_by_id, create_person, update_person, delete_person
)
from sqlalchemy.orm import Session


router = APIRouter(prefix="/api/admin", tags=["admin"])


# Pydantic models for requests
class LoginRequest(BaseModel):
    password: str


class UnitCreateRequest(BaseModel):
    unit_id: str
    title: str
    module_id: int
    semester: Optional[int] = None
    sws: Optional[int] = None
    workload: Optional[str] = None
    lehrsprache: Optional[str] = None
    lernziele: Optional[str] = None
    inhalte: Optional[str] = None
    verantwortliche_ids: List[int] = []


class UnitUpdateRequest(BaseModel):
    unit_id: Optional[str] = None
    title: Optional[str] = None
    module_id: Optional[int] = None
    semester: Optional[int] = None
    sws: Optional[int] = None
    workload: Optional[str] = None
    lehrsprache: Optional[str] = None
    lernziele: Optional[str] = None
    inhalte: Optional[str] = None
    verantwortliche_ids: Optional[List[int]] = None


class ModuleCreateRequest(BaseModel):
    module_id: str
    title: str
    credits: Optional[int] = None
    sws: Optional[int] = None
    semester: Optional[int] = None
    lernziele: Optional[str] = None
    pruefungsleistung: Optional[str] = None


class ModuleUpdateRequest(BaseModel):
    module_id: Optional[str] = None
    title: Optional[str] = None
    credits: Optional[int] = None
    sws: Optional[int] = None
    semester: Optional[int] = None
    lernziele: Optional[str] = None
    pruefungsleistung: Optional[str] = None


class PersonCreateRequest(BaseModel):
    name: str


class PersonUpdateRequest(BaseModel):
    name: Optional[str] = None


# Auth dependency
def verify_auth_token(authorization: Optional[str] = Header(None)) -> None:
    """Verify session token from Authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    # Support both "Bearer <token>" and just "<token>"
    token = authorization.replace("Bearer ", "")

    if not verify_session(token):
        raise HTTPException(status_code=401, detail="Invalid or expired session")


# Login endpoint (no auth required)
@router.post("/login")
def login(request: LoginRequest):
    """Login with admin password and get session token."""
    if not verify_admin_password(request.password):
        raise HTTPException(status_code=401, detail="Invalid password")

    token = create_session()
    return {"token": token}


@router.post("/logout")
def logout(authorization: Optional[str] = Header(None)):
    """Logout and invalidate session token."""
    if authorization:
        token = authorization.replace("Bearer ", "")
        delete_session(token)
    return {"message": "Logged out"}


# Units endpoints
@router.get("/units", dependencies=[Depends(verify_auth_token)])
def list_units():
    """Get all units with relationships."""
    session = get_session()
    try:
        units = get_all_units(session)
        return {
            "units": [
                {
                    "id": u.id,
                    "unit_id": u.unit_id,
                    "title": u.title,
                    "module_id": u.module_id,
                    "module_title": u.module.title if u.module else None,
                    "semester": u.semester,
                    "sws": u.sws,
                    "workload": u.workload,
                    "lehrsprache": u.lehrsprache,
                    "lernziele": u.lernziele,
                    "inhalte": u.inhalte,
                    "verantwortliche": [{"id": p.id, "name": p.name} for p in u.verantwortliche],
                    "created_at": u.created_at.isoformat(),
                    "updated_at": u.updated_at.isoformat(),
                }
                for u in units
            ]
        }
    finally:
        session.close()


@router.get("/units/{unit_id}", dependencies=[Depends(verify_auth_token)])
def get_unit(unit_id: int):
    """Get a single unit by ID."""
    session = get_session()
    try:
        unit = get_unit_by_id(session, unit_id)
        if not unit:
            raise HTTPException(status_code=404, detail="Unit not found")

        return {
            "id": unit.id,
            "unit_id": unit.unit_id,
            "title": unit.title,
            "module_id": unit.module_id,
            "module_title": unit.module.title if unit.module else None,
            "semester": unit.semester,
            "sws": unit.sws,
            "workload": unit.workload,
            "lehrsprache": unit.lehrsprache,
            "lernziele": unit.lernziele,
            "inhalte": unit.inhalte,
            "verantwortliche": [{"id": p.id, "name": p.name} for p in unit.verantwortliche],
            "created_at": unit.created_at.isoformat(),
            "updated_at": unit.updated_at.isoformat(),
        }
    finally:
        session.close()


@router.post("/units", dependencies=[Depends(verify_auth_token)])
def add_unit(request: UnitCreateRequest):
    """Create a new unit."""
    session = get_session()
    try:
        data = request.dict()
        unit = create_unit(session, data)
        return {
            "id": unit.id,
            "unit_id": unit.unit_id,
            "title": unit.title,
            "message": "Unit created successfully"
        }
    finally:
        session.close()


@router.put("/units/{unit_id}", dependencies=[Depends(verify_auth_token)])
def modify_unit(unit_id: int, request: UnitUpdateRequest):
    """Update an existing unit."""
    session = get_session()
    try:
        data = {k: v for k, v in request.dict().items() if v is not None}
        unit = update_unit(session, unit_id, data)
        if not unit:
            raise HTTPException(status_code=404, detail="Unit not found")

        return {
            "id": unit.id,
            "unit_id": unit.unit_id,
            "title": unit.title,
            "message": "Unit updated successfully"
        }
    finally:
        session.close()


@router.delete("/units/{unit_id}", dependencies=[Depends(verify_auth_token)])
def remove_unit(unit_id: int):
    """Delete a unit."""
    session = get_session()
    try:
        success = delete_unit(session, unit_id)
        if not success:
            raise HTTPException(status_code=404, detail="Unit not found")
        return {"message": "Unit deleted successfully"}
    finally:
        session.close()


# Modules endpoints
@router.get("/modules", dependencies=[Depends(verify_auth_token)])
def list_modules():
    """Get all modules."""
    session = get_session()
    try:
        modules = get_all_modules(session)
        return {
            "modules": [
                {
                    "id": m.id,
                    "module_id": m.module_id,
                    "title": m.title,
                    "credits": m.credits,
                    "sws": m.sws,
                    "semester": m.semester,
                    "lernziele": m.lernziele,
                    "pruefungsleistung": m.pruefungsleistung,
                    "created_at": m.created_at.isoformat(),
                    "updated_at": m.updated_at.isoformat(),
                }
                for m in modules
            ]
        }
    finally:
        session.close()


@router.get("/modules/{module_id}", dependencies=[Depends(verify_auth_token)])
def get_module(module_id: int):
    """Get a single module by ID."""
    session = get_session()
    try:
        module = get_module_by_id(session, module_id)
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")

        return {
            "id": module.id,
            "module_id": module.module_id,
            "title": module.title,
            "credits": module.credits,
            "sws": module.sws,
            "semester": module.semester,
            "lernziele": module.lernziele,
            "pruefungsleistung": module.pruefungsleistung,
            "created_at": module.created_at.isoformat(),
            "updated_at": module.updated_at.isoformat(),
        }
    finally:
        session.close()


@router.post("/modules", dependencies=[Depends(verify_auth_token)])
def add_module(request: ModuleCreateRequest):
    """Create a new module."""
    session = get_session()
    try:
        module = create_module(session, request.dict())
        return {
            "id": module.id,
            "module_id": module.module_id,
            "title": module.title,
            "message": "Module created successfully"
        }
    finally:
        session.close()


@router.put("/modules/{module_id}", dependencies=[Depends(verify_auth_token)])
def modify_module(module_id: int, request: ModuleUpdateRequest):
    """Update an existing module."""
    session = get_session()
    try:
        data = {k: v for k, v in request.dict().items() if v is not None}
        module = update_module(session, module_id, data)
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")

        return {
            "id": module.id,
            "module_id": module.module_id,
            "title": module.title,
            "message": "Module updated successfully"
        }
    finally:
        session.close()


@router.delete("/modules/{module_id}", dependencies=[Depends(verify_auth_token)])
def remove_module(module_id: int):
    """Delete a module."""
    session = get_session()
    try:
        success = delete_module(session, module_id)
        if not success:
            raise HTTPException(status_code=404, detail="Module not found")
        return {"message": "Module deleted successfully"}
    finally:
        session.close()


# Personen endpoints
@router.get("/personen", dependencies=[Depends(verify_auth_token)])
def list_personen():
    """Get all personen."""
    session = get_session()
    try:
        personen = get_all_personen(session)
        return {
            "personen": [
                {
                    "id": p.id,
                    "name": p.name,
                    "created_at": p.created_at.isoformat(),
                    "updated_at": p.updated_at.isoformat(),
                }
                for p in personen
            ]
        }
    finally:
        session.close()


@router.get("/personen/{person_id}", dependencies=[Depends(verify_auth_token)])
def get_person(person_id: int):
    """Get a single person by ID."""
    session = get_session()
    try:
        person = get_person_by_id(session, person_id)
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")

        return {
            "id": person.id,
            "name": person.name,
            "created_at": person.created_at.isoformat(),
            "updated_at": person.updated_at.isoformat(),
        }
    finally:
        session.close()


@router.post("/personen", dependencies=[Depends(verify_auth_token)])
def add_person(request: PersonCreateRequest):
    """Create a new person."""
    session = get_session()
    try:
        person = create_person(session, request.dict())
        return {
            "id": person.id,
            "name": person.name,
            "message": "Person created successfully"
        }
    finally:
        session.close()


@router.put("/personen/{person_id}", dependencies=[Depends(verify_auth_token)])
def modify_person(person_id: int, request: PersonUpdateRequest):
    """Update an existing person."""
    session = get_session()
    try:
        data = {k: v for k, v in request.dict().items() if v is not None}
        person = update_person(session, person_id, data)
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")

        return {
            "id": person.id,
            "name": person.name,
            "message": "Person updated successfully"
        }
    finally:
        session.close()


@router.delete("/personen/{person_id}", dependencies=[Depends(verify_auth_token)])
def remove_person(person_id: int):
    """Delete a person."""
    session = get_session()
    try:
        success = delete_person(session, person_id)
        if not success:
            raise HTTPException(status_code=404, detail="Person not found")
        return {"message": "Person deleted successfully"}
    finally:
        session.close()
