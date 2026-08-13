import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.auth.dependencies import AuthContext, authorized_patient
from app.auth.security import hash_password
from app.clinic_resolution.service import ResolvedClinic
from app.core.errors import AppError
from app.database.base import Base
from app.database.models import Branch, Patient, PatientDoctorAssignment, Role, User


@pytest.mark.asyncio
async def test_unassigned_doctor_is_denied_and_assigned_doctor_allowed():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as c:
        await c.run_sync(
            Base.metadata.create_all,
            tables=[t for n, t in Base.metadata.tables.items() if n != "clinic_registry"],
        )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        branch = Branch(name="Fictional Branch", code="FB")
        doctor = User(
            username="doctor",
            email="doctor@example.test",
            password_hash=hash_password("not-a-real-password"),
            role=Role.DOCTOR,
            first_name="Demo",
            last_name="Doctor",
        )
        db.add_all([branch, doctor])
        await db.flush()
        patient = Patient(
            patient_number="FICTION-1",
            first_name="Fictional",
            last_name="Patient",
            branch_id=branch.id,
        )
        db.add(patient)
        await db.commit()
        clinic = ResolvedClinic(uuid.uuid4(), "demo", "Demo", "sqlite+aiosqlite://", [])
        ctx = AuthContext(clinic, doctor, {branch.id}, db)
        with pytest.raises(AppError) as denied:
            await authorized_patient(ctx, patient.id)
        assert denied.value.code == "PATIENT_NOT_AUTHORIZED"
        db.add(
            PatientDoctorAssignment(
                patient_id=patient.id,
                doctor_id=doctor.id,
                branch_id=branch.id,
                assigned_by=doctor.id,
                active=True,
            )
        )
        await db.commit()
        assert (await authorized_patient(ctx, patient.id)).id == patient.id
    await engine.dispose()
