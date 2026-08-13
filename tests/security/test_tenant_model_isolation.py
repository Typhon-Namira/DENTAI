import app.database.control_models  # noqa: F401
import app.database.models  # noqa: F401
from app.database.base import Base


def test_control_plane_has_no_clinical_columns_or_foreign_keys():
    control = Base.metadata.tables["clinic_registry"]
    forbidden = {"patient_id", "doctor_id", "xray_id", "clinical_notes"}
    assert not forbidden.intersection(control.columns.keys())
    assert not list(control.foreign_keys)


def test_clinical_tables_do_not_carry_switchable_clinic_id():
    clinical = [t for name, t in Base.metadata.tables.items() if name != "clinic_registry"]
    assert clinical
    assert all("clinic_id" not in table.columns for table in clinical)
