import uuid

from app.database.control_models import AccessRequest, SalesClinicContact
from app.platform.sales_service import (
    SALES_COMMISSION_RATE_BPS,
    _score_contact,
    normalize_phone,
    normalize_text,
    normalize_website,
)


def access_request() -> AccessRequest:
    return AccessRequest(
        clinic_name="Ararat Dental Center",
        country="Armenia",
        city="Yerevan",
        address="12 Komitas Ave",
        website="https://www.ararat-dental.am/contact",
        contact_name="Ani Petrosyan",
        contact_role="Director",
        email="director@ararat-dental.am",
        phone="+374 91 123 456",
        dentists_count=5,
        branches_count=1,
    )


def reported_contact() -> SalesClinicContact:
    return SalesClinicContact(
        report_id=uuid.uuid4(),
        manager_id=uuid.uuid4(),
        clinic_name="Ararat Dental Center",
        country="Armenia",
        city="Yerevan",
        address="12 Komitas Ave",
        website="ararat-dental.am",
        contact_name="Ani Petrosyan",
        contact_role="Director",
        email="DIRECTOR@ARARAT-DENTAL.AM",
        phone="091123456",
        negotiation_result="Interested in Premium after a product demonstration.",
        outcome="INTERESTED",
        clinic_name_norm=normalize_text("Ararat Dental Center") or "",
        email_norm=normalize_text("DIRECTOR@ARARAT-DENTAL.AM"),
        phone_norm=normalize_phone("091123456"),
        website_norm=normalize_website("ararat-dental.am"),
        city_norm=normalize_text("Yerevan"),
        address_norm=normalize_text("12 Komitas Ave"),
    )


def test_sales_commission_rate_is_fixed_at_thirty_percent() -> None:
    assert SALES_COMMISSION_RATE_BPS == 3000


def test_clinic_identity_normalization_is_stable() -> None:
    assert normalize_text("  ARARAT   Dental Center ") == "ararat dental center"
    assert normalize_phone("+374 (91) 123-456") == "37491123456"
    assert normalize_website("https://www.ArArAt-Dental.am/path") == "ararat-dental.am"


def test_reported_clinic_gets_strong_identity_match_score() -> None:
    score, signals = _score_contact(reported_contact(), access_request())

    assert score >= 100
    assert signals["email"] is True
    assert signals["phone"] is True
    assert signals["website"] is True
    assert signals["clinic_name"] is True
