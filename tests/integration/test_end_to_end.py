import uuid
from io import BytesIO
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.database.sessions as sessions
import app.main as main_module
from app.auth.security import hash_password
from app.clinic_resolution.service import resolver
from app.core.config import get_settings
from app.database.base import Base
from app.database.control_models import ClinicRegistry
from app.database.models import (
    Branch,
    Patient,
    PatientDoctorAssignment,
    Role,
    User,
    UserBranchScope,
)

PASSWORD = "Fictional-Development-Password-47"


async def seed_clinic(path: Path, label: str, shared_patient_id: uuid.UUID) -> dict:
    url = f"sqlite+aiosqlite:///{path.as_posix()}"
    engine = create_async_engine(url)
    async with engine.begin() as connection:
        await connection.run_sync(
            Base.metadata.create_all,
            tables=[
                table for name, table in Base.metadata.tables.items() if name != "clinic_registry"
            ],
        )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db, db.begin():
        branch = Branch(name=f"{label} Branch", code=f"{label}-1")
        director = User(
            username=f"{label.lower()}-director",
            email=f"director@{label.lower()}.example.test",
            password_hash=hash_password(PASSWORD),
            role=Role.DIRECTOR,
            first_name="Fictional",
            last_name="Director",
        )
        manager = User(
            username=f"{label.lower()}-manager",
            email=f"manager@{label.lower()}.example.test",
            password_hash=hash_password(PASSWORD),
            role=Role.MANAGER,
            first_name="Fictional",
            last_name="Manager",
        )
        doctor = User(
            username=f"{label.lower()}-doctor",
            email=f"doctor@{label.lower()}.example.test",
            password_hash=hash_password(PASSWORD),
            role=Role.DOCTOR,
            first_name="Fictional",
            last_name="Doctor",
        )
        db.add_all([branch, director, manager, doctor])
        await db.flush()
        patient = Patient(
            id=shared_patient_id,
            patient_number=f"{label}-P-1",
            first_name="Fictional",
            last_name=f"{label} Patient",
            branch_id=branch.id,
        )
        unassigned = Patient(
            patient_number=f"{label}-P-2",
            first_name="Unassigned",
            last_name="Patient",
            branch_id=branch.id,
        )
        db.add_all([patient, unassigned])
        await db.flush()
        db.add_all(
            [
                UserBranchScope(user_id=manager.id, branch_id=branch.id),
                UserBranchScope(user_id=doctor.id, branch_id=branch.id),
                PatientDoctorAssignment(
                    patient_id=patient.id,
                    doctor_id=doctor.id,
                    branch_id=branch.id,
                    assigned_by=director.id,
                ),
            ]
        )
    await engine.dispose()
    return {
        "url": url,
        "branch": branch.id,
        "director": director.id,
        "manager": manager.id,
        "doctor": doctor.id,
        "patient": patient.id,
        "unassigned": unassigned.id,
    }


@pytest.fixture
async def api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    shared_patient_id = uuid.uuid4()
    clinic_a = await seed_clinic(tmp_path / "clinic-a.db", "A", shared_patient_id)
    clinic_b = await seed_clinic(tmp_path / "clinic-b.db", "B", shared_patient_id)
    control_url = f"sqlite+aiosqlite:///{(tmp_path / 'control.db').as_posix()}"
    control_engine = create_async_engine(control_url)
    async with control_engine.begin() as connection:
        await connection.run_sync(
            Base.metadata.create_all, tables=[Base.metadata.tables["clinic_registry"]]
        )
    control_factory = async_sessionmaker(control_engine, expire_on_commit=False)
    clinic_a_id, clinic_b_id = uuid.uuid4(), uuid.uuid4()
    async with control_factory() as db, db.begin():
        db.add_all(
            [
                ClinicRegistry(
                    id=clinic_a_id,
                    slug="clinic-a",
                    name="Clinic A",
                    encrypted_database_url=f"plain:{clinic_a['url']}",
                    allowed_origins=["https://a.example.test"],
                ),
                ClinicRegistry(
                    id=clinic_b_id,
                    slug="clinic-b",
                    name="Clinic B",
                    encrypted_database_url=f"plain:{clinic_b['url']}",
                    allowed_origins=["https://b.example.test"],
                ),
            ]
        )
    monkeypatch.setattr(sessions, "ControlSession", control_factory)
    monkeypatch.setattr(main_module, "ControlSession", control_factory)
    monkeypatch.setattr(main_module.settings, "local_storage_path", tmp_path / "storage")
    await resolver.dispose_all()
    with TestClient(main_module.app) as client:
        yield client, clinic_a, clinic_b
    await control_engine.dispose()


def login(client: TestClient, clinic: str, identifier: str) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={"clinic_slug": clinic, "identifier": identifier, "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_auth_rotation_scoping_xray_ai_and_review(api):
    client, clinic_a, clinic_b = api
    pair = login(client, "clinic-a", "a-doctor")
    doctor_headers = auth(pair["access_token"])

    assert (
        client.get(
            f"/api/v1/patients/{clinic_a['patient']}/profile", headers=doctor_headers
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/api/v1/patients/{clinic_a['unassigned']}/profile", headers=doctor_headers
        ).status_code
        == 403
    )

    # The same UUID exists in Clinic B, but the Clinic A token can only see Clinic A's row.
    scoped = client.get(
        f"/api/v1/patients/{clinic_b['patient']}/profile",
        headers={**doctor_headers, "X-Clinic-ID": "clinic-b"},
        params={"clinic_id": "clinic-b"},
    )
    assert scoped.status_code == 200
    assert scoped.json()["patient"]["patient_number"] == "A-P-1"

    denied_upload = client.post(
        f"/api/v1/xrays/patients/{clinic_a['unassigned']}",
        headers=doctor_headers,
        files={"file": ("bad.png", b"\x89PNG\r\n\x1a\ncontent", "image/png")},
    )
    assert denied_upload.status_code == 403
    invalid_upload = client.post(
        f"/api/v1/xrays/patients/{clinic_a['patient']}",
        headers=doctor_headers,
        files={"file": ("fake.png", b"not an image", "image/png")},
    )
    assert invalid_upload.status_code == 415
    upload = client.post(
        f"/api/v1/xrays/patients/{clinic_a['patient']}",
        headers=doctor_headers,
        files={"file": ("../scan.png", b"\x89PNG\r\n\x1a\ncontent", "image/png")},
    )
    assert upload.status_code == 201, upload.text
    assert upload.json()["original_filename"] == "scan.png"
    assert "storage_key" not in upload.json()
    xray_id = upload.json()["id"]

    grant = client.get(f"/api/v1/xrays/{xray_id}/download", headers=doctor_headers)
    assert grant.status_code == 200
    assert grant.json()["url"].endswith("/content")
    content = client.get(grant.json()["url"], headers=doctor_headers)
    assert content.status_code == 200
    assert content.headers["cache-control"] == "private, no-store"

    analysis = client.post("/api/v1/ai-analyses", headers=doctor_headers, json={"xray_id": xray_id})
    assert analysis.status_code == 201, analysis.text
    assert analysis.json()["status"] == "COMPLETED"
    profile = client.get(
        f"/api/v1/patients/{clinic_a['patient']}/profile", headers=doctor_headers
    ).json()
    ai_finding = next(item for item in profile["findings"] if item["source"] == "AI")
    review = client.post(
        f"/api/v1/ai-analyses/{analysis.json()['id']}/review",
        headers=doctor_headers,
        json={"decisions": [{"finding_id": ai_finding["id"], "decision": "CONFIRMED"}]},
    )
    assert review.status_code == 200, review.text
    reviewed_profile = client.get(
        f"/api/v1/patients/{clinic_a['patient']}/profile", headers=doctor_headers
    ).json()
    assert {item["source"] for item in reviewed_profile["findings"]} == {"AI", "DENTIST"}

    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": pair["refresh_token"]})
    assert rotated.status_code == 200
    assert (
        client.post(
            "/api/v1/auth/refresh", json={"refresh_token": pair["refresh_token"]}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/logout", json={"refresh_token": rotated.json()["refresh_token"]}
        ).status_code
        == 204
    )
    assert (
        client.post(
            "/api/v1/auth/refresh", json={"refresh_token": rotated.json()["refresh_token"]}
        ).status_code
        == 401
    )


def test_manager_and_director_rbac(api):
    client, clinic_a, _ = api
    manager = login(client, "clinic-a", "a-manager")
    manager_headers = auth(manager["access_token"])
    doctor_create = client.post(
        "/api/v1/users/doctors",
        headers=manager_headers,
        json={
            "username": "new-doctor",
            "email": "new-doctor@example.com",
            "password": PASSWORD,
            "first_name": "New",
            "last_name": "Doctor",
            "branch_ids": [str(clinic_a["branch"])],
        },
    )
    assert doctor_create.status_code == 201, doctor_create.text
    assert "password_hash" not in doctor_create.json()
    assert (
        client.post("/api/v1/users/managers", headers=manager_headers, json={}).status_code == 403
    )
    assert client.get("/api/v1/packages", headers=manager_headers).status_code == 403

    director = login(client, "clinic-a", "a-director")
    director_headers = auth(director["access_token"])
    assert client.get("/api/v1/packages", headers=director_headers).status_code == 200
    assert client.get("/api/v1/audit", headers=director_headers).status_code == 200
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200
    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    assert len(openapi.json()["paths"]) >= 20


def test_failed_login_is_safe_and_security_headers_are_present(api):
    client, _, _ = api
    wrong = client.post(
        "/api/v1/auth/login",
        json={"clinic_slug": "clinic-a", "identifier": "a-doctor", "password": "wrong-pass"},
    )
    assert wrong.status_code == 401
    assert wrong.json()["error"]["code"] == "INVALID_CREDENTIALS"
    unknown = client.post(
        "/api/v1/auth/login",
        json={"clinic_slug": "missing", "identifier": "a-doctor", "password": PASSWORD},
    )
    assert unknown.status_code == 404
    health = client.get("/health", headers={"X-Request-ID": "invalid request id with spaces"})
    assert health.headers["x-content-type-options"] == "nosniff"
    assert health.headers["x-frame-options"] == "DENY"
    assert health.headers["x-request-id"] != "invalid request id with spaces"


def test_real_opg_api_quality_path_operates_without_groq_or_fake_findings(api):
    client, clinic_a, _ = api
    settings = get_settings()
    original_provider = settings.ai_provider
    settings.ai_provider = "real_opg"
    try:
        pair = login(client, "clinic-a", "a-doctor")
        headers = auth(pair["access_token"])
        pixels = np.tile(np.linspace(20, 230, 1024, dtype=np.uint8), (512, 1))
        image = BytesIO()
        Image.fromarray(pixels).save(image, format="PNG")
        upload = client.post(
            f"/api/v1/xrays/patients/{clinic_a['patient']}",
            headers=headers,
            files={"file": ("synthetic-opg.png", image.getvalue(), "image/png")},
        )
        assert upload.status_code == 201, upload.text
        analysis = client.post(
            "/api/v1/ai-analyses", headers=headers, json={"xray_id": upload.json()["id"]}
        )
        assert analysis.status_code == 202, analysis.text
        payload = analysis.json()
        assert payload["status"] == "QUEUED"
        assert payload["structured_result"] is None
        assert payload["attempt_count"] == 0
    finally:
        settings.ai_provider = original_provider
