"""Provider-neutral product domain models."""
from __future__ import annotations
from datetime import date,datetime,timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel,ConfigDict,Field

def utcnow(): return datetime.now(timezone.utc)
class StrictModel(BaseModel): model_config=ConfigDict(extra="forbid")
class IdentityStatus(str,Enum):
 IDENTITY_NOT_FOUND="IDENTITY_NOT_FOUND";IDENTITY_EXTRACTED="IDENTITY_EXTRACTED";IDENTITY_NEEDS_CONFIRMATION="IDENTITY_NEEDS_CONFIRMATION";IDENTITY_CONFIRMED="IDENTITY_CONFIRMED";IDENTITY_CONFLICT="IDENTITY_CONFLICT"
class IdentityAction(str,Enum): CONFIRM="CONFIRM";CORRECT="CORRECT";SELECT_EXISTING_PATIENT="SELECT_EXISTING_PATIENT";CREATE_NEW_PATIENT="CREATE_NEW_PATIENT"
class ProductIdentityState(str,Enum):
 IDENTITY_FOUND="IDENTITY_FOUND";IDENTITY_NOT_FOUND="IDENTITY_NOT_FOUND";IDENTITY_REVIEW_REQUIRED="IDENTITY_REVIEW_REQUIRED";IDENTITY_MATCHED_EXISTING="IDENTITY_MATCHED_EXISTING";IDENTITY_NEW_PATIENT_CANDIDATE="IDENTITY_NEW_PATIENT_CANDIDATE"
class RiskLevel(str,Enum): URGENT_REVIEW="URGENT_REVIEW";HIGH="HIGH";MEDIUM="MEDIUM";LOW="LOW";ROUTINE="ROUTINE"
class ReviewAction(str,Enum): CONFIRM="CONFIRM";REJECT="REJECT";CORRECT="CORRECT";ADD_FINDING="ADD_FINDING";ADD_NOTE="ADD_NOTE";MODIFY_STATUS="MODIFY_STATUS";MODIFY_FDI="MODIFY_FDI"
class LabelState(str,Enum): UNLABELED="UNLABELED";AI_PRELABELED="AI_PRELABELED";NEEDS_REVIEW="NEEDS_REVIEW";HUMAN_CORRECTED="HUMAN_CORRECTED";VERIFIED="VERIFIED";TRAIN_READY="TRAIN_READY"
class ChangeState(str,Enum): STABLE="STABLE";STABLE_WITH_CONFIDENCE_CHANGE="STABLE_WITH_CONFIDENCE_CHANGE";IMPROVED="IMPROVED";PROGRESSED="PROGRESSED";NEW_FINDING="NEW_FINDING";RESOLVED="RESOLVED";UNKNOWN="UNKNOWN";CHANGE_UNCERTAIN="CHANGE_UNCERTAIN"
class ExtractedField(StrictModel): value:str|None=None;source:str;confidence:float=Field(ge=0,le=1);verified:bool=False;normalized_value:str|None=None;source_region:list[float]|None=None
class ExtractedIdentity(StrictModel):
 patient_name:ExtractedField|None=None;patient_id:ExtractedField|None=None;date_of_birth:ExtractedField|None=None;age:ExtractedField|None=None;sex:ExtractedField|None=None;study_date:ExtractedField|None=None;clinic_name:ExtractedField|None=None;metadata:dict[str,ExtractedField]=Field(default_factory=dict)
class Patient(StrictModel):
 patient_id:str;clinic_id:str;clinic_patient_number:str|None=None;first_name:str|None=None;last_name:str|None=None;full_name:str|None=None;date_of_birth:date|None=None;sex:str|None=None;phone:str|None=None;email:str|None=None;external_patient_id:str|None=None;dicom_patient_id:str|None=None;created_at:datetime=Field(default_factory=utcnow);updated_at:datetime=Field(default_factory=utcnow)
class PatientMatch(StrictModel): patient_id:str;match_score:float=Field(ge=0,le=1);match_reasons:list[str]
class IdentityResolution(StrictModel): status:IdentityStatus;extracted_identity:ExtractedIdentity;candidate_patient_matches:list[PatientMatch]=Field(default_factory=list);requires_confirmation:bool=True;confidence:float=0;conflict_reasons:list[str]=Field(default_factory=list)
class FollowupWindow(StrictModel): min_months:int=Field(ge=0);max_months:int=Field(ge=0)
class FollowupRecommendation(StrictModel): risk_level:RiskLevel;followup_window:FollowupWindow;recommended_followup_start:date;recommended_followup_end:date;target_followup_date:date;reasons:list[str];source_findings:list[str]=Field(default_factory=list);tooth_fdi:str|None=None;rule_ids:list[str]=Field(default_factory=list);rule_version:str="1.0";status:str="OPEN";doctor_overridden:bool=False;disclaimer:str="Product-configured reassessment timing; not a predicted disease occurrence date."
class Reminder(StrictModel): reminder_id:str;clinic_id:str;patient_id:str;case_id:str;tooth_fdi:str|None=None;reminder_type:str;scheduled_at:datetime;channel:str;status:str="SCHEDULED";message_template:str;created_by:str;created_at:datetime=Field(default_factory=utcnow)
class AuditEvent(StrictModel):
 audit_id:str;clinic_id:str;user_id:str|None=None;patient_id:str|None=None;case_id:str|None=None;action:str;entity_type:str;entity_id:str;timestamp:datetime=Field(default_factory=utcnow);before_reference:str|None=None;after_reference:str|None=None;ip_address:str|None=None;request_id:str|None=None
class Study(StrictModel): study_id:str;clinic_id:str;patient_id:str|None=None;source_type:str;study_date:date|None=None;storage_reference:dict[str,Any];created_at:datetime=Field(default_factory=utcnow)
class ImmutableAnalysis(StrictModel): model_config=ConfigDict(extra="allow",frozen=True);analysis_id:str;study_id:str;model_version:str;model_manifest_hash:str;thresholds:dict[str,Any];analysis_timestamp:datetime;ai_output:dict[str,Any]
class DoctorReview(StrictModel): model_config=ConfigDict(frozen=True);review_id:str;clinic_id:str;analysis_id:str;tooth_fdi:str|None=None;finding_type:str|None=None;doctor_id:str;timestamp:datetime=Field(default_factory=utcnow);original_ai_output:dict[str,Any];doctor_action:ReviewAction;corrected_value:Any=None;notes:str|None=None
class LearningRecord(StrictModel): learning_record_id:str;clinic_id:str;source_case_id:str;source_model_version:str;verification_status:LabelState;deidentification_status:str;training_eligibility:bool=False;consent_or_policy_reference:str|None=None;deidentified_asset_reference:str|None=None;original_asset_reference:str|None=None;original_ai_output_reference:str|None=None;correction_payload:dict[str,Any]|None=None;reviewer_id:str|None=None;review_timestamp:datetime|None=None
class PatientProfile(StrictModel):
 patient_id:str;clinic_id:str;display_name:str|None=None;clinic_local_identifier:str|None=None;date_of_birth:date|None=None;identity_confidence:float=Field(default=1.0,ge=0,le=1);identity_state:ProductIdentityState=ProductIdentityState.IDENTITY_FOUND;created_at:datetime=Field(default_factory=utcnow);updated_at:datetime=Field(default_factory=utcnow)
class IdentityCandidate(StrictModel):
 candidate_id:str;clinic_id:str;study_id:str;state:ProductIdentityState;extracted_identity:ExtractedIdentity;candidate_matches:list[PatientMatch]=Field(default_factory=list);raw_ocr_text:str|None=None;created_at:datetime=Field(default_factory=utcnow)
class StudyRecord(StrictModel):
 study_id:str;clinic_id:str;patient_id:str|None=None;original_image_reference:dict[str,Any];study_date:date|None=None;identity_state:ProductIdentityState;review_status:str="UNREVIEWED";created_at:datetime=Field(default_factory=utcnow)
class AnalysisRecord(StrictModel):
 model_config=ConfigDict(extra="forbid",frozen=True);analysis_id:str;clinic_id:str;study_id:str;patient_id:str|None=None;model_version:str;model_manifest_hash:str;thresholds:dict[str,Any];analysis_timestamp:datetime=Field(default_factory=utcnow);raw_ai_output:dict[str,Any];product_output:dict[str,Any]
class FollowupEvent(StrictModel):
 follow_up_id:str;clinic_id:str;patient_id:str;study_id:str;analysis_id:str;tooth_fdi:str|None=None;priority:RiskLevel;target_date:date;reason:list[str];source_finding:list[str];rule_ids:list[str];rule_version:str;status:str="OPEN";created_at:datetime=Field(default_factory=utcnow);completed_at:datetime|None=None;completed_by:str|None=None
class DentaiCaseAnalysis(StrictModel): case_id:str;clinic_id:str;patient:dict[str,Any]|None;identity_status:IdentityStatus;identity:IdentityResolution;study:Study;model:dict[str,Any];analysis:dict[str,Any];overlay:dict[str,Any];tooth_results:list[dict[str,Any]];followup:dict[str,Any];longitudinal_comparison:dict[str,Any]|None;review_summary:dict[str,Any];learning_status:dict[str,Any]
