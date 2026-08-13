CANONICAL_FINDINGS = frozenset(
    {
        "TOOTH",
        "MISSING_TOOTH",
        "FILLING",
        "CROWN",
        "BRIDGE",
        "IMPLANT",
        "ROOT_CANAL_TREATED",
        "ENDODONTIC_POST",
        "IMPACTED_TOOTH",
        "CARIES_SUSPECTED",
        "PERIAPICAL_LESION",
        "ALVEOLAR_BONE_LOSS",
        "BROKEN_DOWN_TOOTH",
        "ROOT_FRAGMENT",
        "ROOT_RESORPTION",
        "FURCATION_LESION",
    }
)

ALIASES = {
    "root canal": "ROOT_CANAL_TREATED",
    "rct": "ROOT_CANAL_TREATED",
    "periapical radiolucency": "PERIAPICAL_LESION",
    "bone resorption": "ALVEOLAR_BONE_LOSS",
    "prosthesis": "BRIDGE",
}


def normalize_label(source_label: str) -> str:
    normalized = source_label.strip().lower().replace("_", " ")
    candidate = ALIASES.get(normalized, normalized.upper().replace(" ", "_"))
    if candidate not in CANONICAL_FINDINGS:
        raise ValueError(f"unmapped source label: {source_label}")
    return candidate
