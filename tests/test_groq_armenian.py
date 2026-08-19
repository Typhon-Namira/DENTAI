import pytest

from ai_engine.groq.armenian import (
    ARMENIAN_LANGUAGE_INSTRUCTION,
    GroqArmenianLanguageError,
    validate_armenian_summary,
)
from ai_engine.groq.provider import GroqClinicalSummary, GroqToothExplanation


def armenian_summary() -> GroqClinicalSummary:
    return GroqClinicalSummary(
        doctor_summary=(
            "Կառուցվածքային տվյալները հասանելի են բժշկի գնահատման համար։ "
            "Արդյունքները պետք է համադրվեն կլինիկական զննման հետ։"
        ),
        tooth_explanations=[
            GroqToothExplanation(
                tooth_fdi="37",
                evidence_ids=["finding_0"],
                headline="37-րդ ատամ — բժշկի գնահատում",
                clinical_explanation=(
                    "Այս ատամի համար համակարգում գրանցված է կառուցվածքային նշան, "
                    "որը ներկայացվում է որպես օժանդակ տեղեկատվություն։"
                ),
                review_explanation=(
                    "Տվյալ նշանը պետք է ստուգվի բժշկի կողմից և համադրվի կլինիկական պատկերի հետ։"
                ),
            )
        ],
        important_changes=["Պահպանել կլինիկական համադրումը և նախորդ տվյալների համեմատությունը։"],
        monitoring_points=["Հաջորդ այցի ժամանակ կրկին գնահատել նշված ատամի շրջանը։"],
        questions_for_doctor=["Արդյո՞ք պատկերը համապատասխանում է կլինիկական զննման արդյունքներին։"],
        patient_message_draft=(
            "Խնդրում ենք կապվել կլինիկայի հետ՝ հաջորդ վերահսկիչ այցը պլանավորելու համար։"
        ),
    )


def test_armenian_guard_accepts_natural_eastern_armenian() -> None:
    summary = armenian_summary()
    assert validate_armenian_summary(summary) is summary


def test_armenian_guard_rejects_english_or_mixed_clinical_prose() -> None:
    summary = armenian_summary()
    summary.doctor_summary = "Կառուցվածքային տվյալները available են բժշկի գնահատման համար։"

    with pytest.raises(GroqArmenianLanguageError):
        validate_armenian_summary(summary)


def test_prompt_requires_eastern_armenian_and_preserves_machine_identifiers() -> None:
    assert "EASTERN ARMENIAN ONLY" in ARMENIAN_LANGUAGE_INSTRUCTION
    assert "Do not answer in English" in ARMENIAN_LANGUAGE_INSTRUCTION
    assert "tooth_fdi" in ARMENIAN_LANGUAGE_INSTRUCTION
    assert "evidence_ids" in ARMENIAN_LANGUAGE_INSTRUCTION
    assert "15-րդ" in ARMENIAN_LANGUAGE_INSTRUCTION


def test_prompt_enforces_native_armenian_dental_vocabulary() -> None:
    assert "լցոնում" in ARMENIAN_LANGUAGE_INSTRUCTION
    assert "պսակ" in ARMENIAN_LANGUAGE_INSTRUCTION
    assert "արմատախողովակային բուժում" in ARMENIAN_LANGUAGE_INSTRUCTION
    assert "խորը կարիես" in ARMENIAN_LANGUAGE_INSTRUCTION
    assert "ֆիլինգ" in ARMENIAN_LANGUAGE_INSTRUCTION
    assert "կրոն" in ARMENIAN_LANGUAGE_INSTRUCTION
    assert "ռուտային թերապիա" in ARMENIAN_LANGUAGE_INSTRUCTION
    assert "խորը աքսիդներ" in ARMENIAN_LANGUAGE_INSTRUCTION
