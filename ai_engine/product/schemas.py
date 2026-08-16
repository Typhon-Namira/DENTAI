"""Future JSON API contracts; transport and database independent."""
from typing import Any
from pydantic import Field
from .models import StrictModel,Patient,DentaiCaseAnalysis
class CreatePatientRequest(StrictModel): clinic_id:str;clinic_patient_number:str|None=None;full_name:str|None=None;date_of_birth:str|None=None;sex:str|None=None;phone:str|None=None;email:str|None=None;external_patient_id:str|None=None
class PatientResponse(StrictModel): patient:Patient
class CreateStudyRequest(StrictModel): clinic_id:str;patient_id:str|None=None;storage_reference:dict[str,Any];source_type:str
class StudyResponse(StrictModel): study:dict[str,Any]
class AnalyzeStudyResponse(StrictModel): analysis:DentaiCaseAnalysis
class OverlayResponse(StrictModel): analysis_id:str;overlay:dict[str,Any]
class IdentityConfirmRequest(StrictModel): clinic_id:str;action:str;patient_id:str|None=None;corrections:dict[str,Any]=Field(default_factory=dict)
class ReviewRequest(StrictModel): clinic_id:str;analysis_id:str;doctor_id:str;action:str;tooth_fdi:str|None=None;finding_type:str|None=None;corrected_value:Any=None;notes:str|None=None
class TimelineResponse(StrictModel): patient_id:str;clinic_id:str;studies:list[dict[str,Any]]
class FollowupRequest(StrictModel): clinic_id:str;patient_id:str;case_id:str;tooth_fdi:str|None=None;risk_override:str|None=None;target_date:str|None=None
class ReminderRequest(StrictModel): clinic_id:str;patient_id:str;case_id:str;scheduled_at:str;channel:str;message_template:str
class LearningStatusResponse(StrictModel): patient_id:str;records:list[dict[str,Any]]
class ToothHistoryResponse(StrictModel): patient_id:str;clinic_id:str;fdi:str;history:list[dict[str,Any]]
class StudyIdentityReviewRequest(StrictModel): action:str;candidate_id:str|None=None;patient_id:str|None=None;verified_fields:dict[str,Any]=Field(default_factory=dict)
class AssignStudyPatientRequest(StrictModel): patient_id:str;identity_confirmation_id:str
class StudyDoctorReviewRequest(StrictModel): action:str;tooth_fdi:str|None=None;finding_type:str|None=None;previous_value:Any=None;new_value:Any=None;notes:str|None=None
class FollowupListResponse(StrictModel): study_id:str;items:list[dict[str,Any]]
class FollowupCompleteRequest(StrictModel): completion_notes:str|None=None
class DashboardResponse(StrictModel): study_id:str;dashboard:dict[str,Any]
API_CONTRACTS={'POST /patients':CreatePatientRequest,'GET /patients/{patient_id}':PatientResponse,'POST /studies':CreateStudyRequest,'GET /studies/{study_id}':StudyResponse,'POST /studies/{study_id}/analyze':AnalyzeStudyResponse,'GET /analyses/{analysis_id}':AnalyzeStudyResponse,'GET /studies/{study_id}/overlay':OverlayResponse,'GET /studies/{study_id}/dashboard':DashboardResponse,'POST /studies/{study_id}/identity/review':StudyIdentityReviewRequest,'POST /studies/{study_id}/assign-patient':AssignStudyPatientRequest,'POST /studies/{study_id}/doctor-review':StudyDoctorReviewRequest,'GET /patients/{patient_id}/timeline':TimelineResponse,'GET /patients/{patient_id}/teeth/{fdi}':ToothHistoryResponse,'GET /studies/{study_id}/follow-ups':FollowupListResponse,'POST /follow-ups/{follow_up_id}/complete':FollowupCompleteRequest,'POST /reminders':ReminderRequest,'GET /patients/{patient_id}/learning-status':LearningStatusResponse}
