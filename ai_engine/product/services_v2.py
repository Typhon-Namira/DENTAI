"""Product Intelligence V2 application service boundaries."""
from __future__ import annotations
import hashlib
from copy import deepcopy
from datetime import date
from pathlib import Path
from .audit import audit_event
from .dashboard import build_dashboard
from .doctor_review import create_review
from .identity_v2 import decide_identity_state,profile_to_patient
from .learning_vault import create_learning_record
from .longitudinal import compare_patient_exams
from .models import *
from .opg_overlay import build_overlay,side_panel
from .patient_matching import rank_patient_matches,new_id,normalize_text
from .risk_followup import FollowupEngine
from .store import ProductStore

MANIFEST=Path("artifacts/production/dentai_v5_model_manifest.json")

class ProductIntelligenceService:
    def __init__(self,store:ProductStore|None=None):self.store=store or ProductStore();self.followup=FollowupEngine()

    def create_patient(self,*,clinic_id:str,patient_id:str,display_name:str|None=None,clinic_local_identifier:str|None=None,date_of_birth:date|None=None,actor_id:str="SYSTEM")->PatientProfile:
        row=PatientProfile(patient_id=patient_id,clinic_id=clinic_id,display_name=display_name,clinic_local_identifier=clinic_local_identifier,date_of_birth=date_of_birth,identity_state=ProductIdentityState.IDENTITY_FOUND)
        self.store.create_patient(row);self.store.append_audit(audit_event(clinic_id=clinic_id,user_id=actor_id,patient_id=patient_id,action="PATIENT_CREATED",entity_type="Patient",entity_id=patient_id));return row

    def match_identity(self,clinic_id:str,identity:ExtractedIdentity)->tuple[ProductIdentityState,list[PatientMatch]]:
        profiles=self.store.clinic_patients(clinic_id);matches=rank_patient_matches(clinic_id,identity,[profile_to_patient(p) for p in profiles]);state=decide_identity_state(identity,matches)
        if state==ProductIdentityState.IDENTITY_MATCHED_EXISTING and identity.patient_name and matches:
            matched=next(p for p in profiles if p.patient_id==matches[0].patient_id)
            if matched.display_name and normalize_text(matched.display_name)!=normalize_text(identity.patient_name.value):state=ProductIdentityState.IDENTITY_REVIEW_REQUIRED
        return state,matches

    def create_study(self,*,clinic_id:str,image_reference:dict,identity:ExtractedIdentity,study_date:date|None=None,actor_id:str="SYSTEM",study_id:str|None=None)->tuple[StudyRecord,list[PatientMatch]]:
        state,matches=self.match_identity(clinic_id,identity);patient_id=matches[0].patient_id if state==ProductIdentityState.IDENTITY_MATCHED_EXISTING else None
        row=StudyRecord(study_id=study_id or new_id("STD"),clinic_id=clinic_id,patient_id=patient_id,original_image_reference=deepcopy(image_reference),study_date=study_date,identity_state=state)
        self.store.append_study(row);self.store.append_audit(audit_event(clinic_id=clinic_id,user_id=actor_id,patient_id=patient_id,case_id=row.study_id,action="STUDY_CREATED",entity_type="Study",entity_id=row.study_id));return row,matches

    def assign_patient(self,clinic_id:str,study_id:str,patient_id:str,actor_id:str)->StudyRecord:
        row=self.store.assign_study(clinic_id,study_id,patient_id);self.store.append_audit(audit_event(clinic_id=clinic_id,user_id=actor_id,patient_id=patient_id,case_id=study_id,action="STUDY_ASSIGNED",entity_type="Study",entity_id=study_id));return row

    def analyze(self,*,clinic_id:str,study_id:str,raw_ai_output:dict,analysis_date:date,actor_id:str="SYSTEM")->AnalysisRecord:
        study=self.store.studies[(clinic_id,study_id)];prior=None
        if study.patient_id:
            timeline=self.store.timeline(clinic_id,study.patient_id);prior_analyses=[a for item in timeline for a in item["analyses"]]
            prior=prior_analyses[-1].raw_ai_output if prior_analyses else None
        recommendations={str(t["fdi"]):self.followup.recommend(t,analysis_date).model_dump(mode="json") for t in raw_ai_output["teeth"]}
        overlay=build_overlay(raw_ai_output,recommendations);comparison=compare_patient_exams(prior,raw_ai_output) if prior else None
        profile=self.store.get_patient(clinic_id,study.patient_id) if study.patient_id else None
        product={"overlay":overlay,"tooth_results":[{**t,"side_panel":side_panel(t)} for t in overlay["teeth"]],"followup":{"per_tooth":recommendations},"longitudinal_comparison":comparison,"identity_state":study.identity_state,"patient_id":study.patient_id}
        product["dashboard"]=build_dashboard({"patient":{"patient_id":profile.patient_id,"name":profile.display_name,"clinic_local_identifier":profile.clinic_local_identifier,"date_of_birth":profile.date_of_birth.isoformat() if profile.date_of_birth else None,"study_date":study.study_date.isoformat() if study.study_date else None,"verified":True} if profile else None,"overlay":overlay,"tooth_results":product["tooth_results"],"followup":product["followup"],"longitudinal_comparison":comparison})
        manifest_hash=hashlib.sha256(MANIFEST.read_bytes()).hexdigest();analysis_id=new_id("ANL")
        row=AnalysisRecord(analysis_id=analysis_id,clinic_id=clinic_id,study_id=study_id,patient_id=study.patient_id,model_version="dentai-unified-v5",model_manifest_hash=manifest_hash,thresholds=deepcopy(raw_ai_output["thresholds"]),raw_ai_output=deepcopy(raw_ai_output),product_output=product)
        self.store.append_analysis(row);self.store.append_audit(audit_event(clinic_id=clinic_id,user_id=actor_id,patient_id=study.patient_id,case_id=study_id,action="AI_ANALYSIS_RUN",entity_type="Analysis",entity_id=analysis_id))
        if study.patient_id:
            for fdi,rec in recommendations.items():
                event=FollowupEvent(follow_up_id=new_id("FUP"),clinic_id=clinic_id,patient_id=study.patient_id,study_id=study_id,analysis_id=analysis_id,tooth_fdi=fdi,priority=rec["risk_level"],target_date=rec["target_followup_date"],reason=rec["reasons"],source_finding=rec["source_findings"],rule_ids=rec["rule_ids"],rule_version=rec["rule_version"])
                self.store.append_followup(event)
        return row

    def doctor_review(self,*,clinic_id:str,analysis_id:str,doctor_id:str,action:str,tooth_fdi:str|None=None,corrected_value=None,notes:str|None=None)->DoctorReview:
        analysis=self.store.analyses[(clinic_id,analysis_id)];original=analysis.raw_ai_output
        if tooth_fdi:original=next(t for t in analysis.raw_ai_output["teeth"] if str(t["fdi"])==str(tooth_fdi))
        review=create_review(clinic_id,analysis_id,doctor_id,original,action,tooth_fdi=tooth_fdi,corrected_value=corrected_value,notes=notes);self.store.append_review(review)
        learning=create_learning_record(clinic_id,analysis.study_id,analysis.model_version,verification_status=LabelState.HUMAN_CORRECTED,deidentification_status="PENDING").model_copy(update={"original_asset_reference":analysis.study_id,"original_ai_output_reference":analysis.analysis_id,"correction_payload":{"action":action,"tooth_fdi":tooth_fdi,"corrected_value":deepcopy(corrected_value)},"reviewer_id":doctor_id,"review_timestamp":review.timestamp})
        self.store.append_learning(learning);self.store.append_audit(audit_event(clinic_id=clinic_id,user_id=doctor_id,patient_id=analysis.patient_id,case_id=analysis.study_id,action="DOCTOR_REVIEWED",entity_type="Analysis",entity_id=analysis_id,before_reference=f"analysis:{analysis_id}",after_reference=f"review:{review.review_id}"));return review

    def complete_followup(self,clinic_id:str,follow_up_id:str,doctor_id:str)->FollowupEvent:
        row=self.store.complete_followup(clinic_id,follow_up_id,doctor_id);self.store.append_audit(audit_event(clinic_id=clinic_id,user_id=doctor_id,patient_id=row.patient_id,case_id=row.study_id,action="FOLLOWUP_COMPLETED",entity_type="Followup",entity_id=follow_up_id));return row
