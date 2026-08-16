"""Deterministic dentist-facing explanations from structured evidence."""
LABELS={
 "CARIES":"a finding compatible with caries","DEEP_CARIES":"a deep-caries risk signal",
 "APICAL_PERIODONTITIS":"an apical periodontal finding","IMPACTED":"an impacted-tooth finding",
 "ROOT_FRAGMENT":"a possible root fragment","BONE_RESORPTION":"an experimental bone-resorption signal",
 "FURCATION_LESION":"an experimental furcation signal","FILLING":"a filling/restoration",
 "IMPLANT":"an implant","CROWN":"a crown","ROOT_CANAL_TREATMENT":"root canal treatment evidence",
 "RESIDUAL_ROOT":"a residual-root finding","HEALTHY":"no abnormal finding from the current fused output",
}

def explain_finding(finding:str,fdi:str,confidence:float|None=None)->str:
    phrase=LABELS.get(finding,f"a {finding.lower().replace('_',' ')} finding")
    qualifier="AI detected" if confidence is None or confidence>=.70 else "AI detected a lower-confidence signal compatible with"
    if qualifier.endswith("with"):text=f"{qualifier} {phrase.removeprefix('a ')} on tooth {fdi}."
    else:text=f"{qualifier} {phrase} on tooth {fdi}."
    return text+" Clinical review is recommended."

def tooth_explanations(tooth:dict)->list[dict]:
    return [{"finding":item["type"],"text":explain_finding(item["type"],str(tooth["fdi"]),item.get("confidence")),"intended_audience":"DENTIST","certainty_boundary":"DECISION_SUPPORT"} for item in tooth.get("findings",[])]
