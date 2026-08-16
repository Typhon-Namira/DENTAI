"""Framework-neutral dashboard presentation integrated with product API responses."""
from .explanations import tooth_explanations

DEFAULT_TOGGLES={"TEETH":True,"FDI":True,"PATHOLOGY":True,"RESTORATIONS":True,"STATUS":True,"CONFIDENCE":False,"DEBUG":False}
PRIORITY_ORDER={"URGENT_REVIEW":0,"HIGH":1,"MEDIUM":2,"LOW":3,"ROUTINE":4,None:5}

def patient_panel(case:dict)->dict:
    patient=case.get("patient")
    if not patient:return {"display_state":"PATIENT_NOT_IDENTIFIED","message":"Patient not identified","patient":None,"actions":["ASSIGN_EXISTING_PATIENT","CREATE_FROM_VERIFIED_INFORMATION"]}
    return {"display_state":"IDENTITY_CONFIRMED" if patient.get("verified") else "IDENTITY_REQUIRES_REVIEW","message":None if patient.get("verified") else "Identity requires review","patient":patient,"actions":["CONFIRM_IDENTITY","REJECT_IDENTITY","ASSIGN_EXISTING_PATIENT"]}

def build_dashboard(case:dict)->dict:
    teeth=[]
    for tooth in case["tooth_results"]:
        detail={**tooth,"explanations":tooth_explanations(tooth),"selected":False}
        teeth.append(detail)
    urgent=[t for t in teeth if t.get("risk_level") in ("URGENT_REVIEW","HIGH")]
    review=[t for t in teeth if t.get("review_required")]
    follow=[t for t in teeth if t.get("risk_level") not in (None,"ROUTINE")]
    restorations=sum(bool(t.get("restoration_boxes")) for t in teeth);pathologies=sum(bool(t.get("pathology_boxes")) for t in teeth)
    priorities=sorted(({"fdi":t["fdi"],"priority":t.get("risk_level"),"findings":[x["type"] for x in t["findings"]],"review_required":t["review_required"]} for t in teeth),key=lambda x:(PRIORITY_ORDER[x["priority"]],int(x["fdi"])))
    recommendations=[]
    for fdi,item in case["followup"]["per_tooth"].items():
        recommendations.append({"fdi":fdi,"target_date":item["target_followup_date"],"priority":item["risk_level"],"reason":item["reasons"],"source_finding":item.get("source_findings",[]),"rule_ids":item.get("rule_ids",[]),"rule_version":item.get("rule_version"),"status":item.get("status","OPEN"),"language":"AI-assisted reassessment recommendation; not a predicted event."})
    return {"schema_version":"dentai-dashboard-v2","layout":{"left":"PATIENT_AND_ANALYSIS_SUMMARY","center":"PRIMARY_OPG_VIEWER","right":"CLINICAL_INTELLIGENCE","bottom":"TOOTH_TIMELINE_AND_FOLLOW_UP"},"patient_panel":patient_panel(case),"opg":{"image":case["overlay"]["image"],"coordinate_space":case["overlay"]["coordinate_space"],"layer_toggles":DEFAULT_TOGGLES,"overlay":case["overlay"],"selectable_teeth":teeth},"clinical_intelligence":{"overall_assessment":{"teeth_analyzed":len(teeth),"urgent_findings":len(urgent),"findings_requiring_review":len(review),"followup_candidates":len(follow),"restoration_findings":restorations,"pathology_findings":pathologies},"priority_findings":priorities,"follow_up":recommendations,"disclaimer":"Current AI-assisted findings and configurable reassessment recommendations require clinical review."},"timeline":{"available":case.get("longitudinal_comparison") is not None,"comparison":case.get("longitudinal_comparison"),"allowed_change_labels":["CURRENT","PREVIOUS","NO_CHANGE","CHANGE_UNCERTAIN"]}}
