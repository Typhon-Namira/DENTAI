"""Tenant-safe append-only reference store used by services and acceptance tests.

Production adapters implement the same boundary with PostgreSQL transactions.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass,field
from datetime import UTC,datetime
from .models import PatientProfile,StudyRecord,AnalysisRecord,DoctorReview,FollowupEvent,AuditEvent,LearningRecord

class NotFoundError(LookupError): pass
class TenantAccessError(PermissionError): pass
class ImmutableRecordError(RuntimeError): pass

@dataclass
class ProductStore:
    patients:dict[tuple[str,str],PatientProfile]=field(default_factory=dict)
    studies:dict[tuple[str,str],StudyRecord]=field(default_factory=dict)
    analyses:dict[tuple[str,str],AnalysisRecord]=field(default_factory=dict)
    reviews:list[DoctorReview]=field(default_factory=list)
    followups:dict[tuple[str,str],FollowupEvent]=field(default_factory=dict)
    audits:list[AuditEvent]=field(default_factory=list)
    learning:list[LearningRecord]=field(default_factory=list)

    def create_patient(self,patient:PatientProfile)->PatientProfile:
        key=(patient.clinic_id,patient.patient_id)
        if key in self.patients:raise ValueError("patient already exists in clinic")
        self.patients[key]=deepcopy(patient);return deepcopy(patient)

    def get_patient(self,clinic_id:str,patient_id:str)->PatientProfile:
        row=self.patients.get((clinic_id,patient_id))
        if row:return deepcopy(row)
        if any(pid==patient_id for _,pid in self.patients):raise TenantAccessError("cross-clinic patient access denied")
        raise NotFoundError("patient not found")

    def clinic_patients(self,clinic_id:str)->list[PatientProfile]:
        return [deepcopy(v) for (clinic,_),v in self.patients.items() if clinic==clinic_id]

    def append_study(self,study:StudyRecord)->StudyRecord:
        key=(study.clinic_id,study.study_id)
        if key in self.studies:raise ImmutableRecordError("historical study cannot be overwritten")
        if study.patient_id:self.get_patient(study.clinic_id,study.patient_id)
        self.studies[key]=deepcopy(study);return deepcopy(study)

    def assign_study(self,clinic_id:str,study_id:str,patient_id:str)->StudyRecord:
        self.get_patient(clinic_id,patient_id);key=(clinic_id,study_id)
        old=self.studies.get(key)
        if not old:raise NotFoundError("study not found")
        if old.patient_id and old.patient_id!=patient_id:raise ImmutableRecordError("assigned patient requires an audited identity review")
        updated=old.model_copy(update={"patient_id":patient_id})
        self.studies[key]=updated;return deepcopy(updated)

    def append_analysis(self,analysis:AnalysisRecord)->AnalysisRecord:
        key=(analysis.clinic_id,analysis.analysis_id)
        if key in self.analyses:raise ImmutableRecordError("analysis cannot be overwritten")
        study=self.studies.get((analysis.clinic_id,analysis.study_id))
        if not study:raise NotFoundError("study not found")
        if analysis.patient_id and study.patient_id!=analysis.patient_id:raise TenantAccessError("analysis patient/study mismatch")
        self.analyses[key]=deepcopy(analysis);return deepcopy(analysis)

    def append_review(self,review:DoctorReview)->DoctorReview:
        if not any(a.clinic_id==review.clinic_id and a.analysis_id==review.analysis_id for a in self.analyses.values()):raise NotFoundError("analysis not found")
        self.reviews.append(deepcopy(review));return deepcopy(review)

    def append_audit(self,event:AuditEvent)->AuditEvent:
        self.audits.append(deepcopy(event));return deepcopy(event)

    def append_learning(self,record:LearningRecord)->LearningRecord:
        self.learning.append(deepcopy(record));return deepcopy(record)

    def append_followup(self,event:FollowupEvent)->FollowupEvent:
        self.get_patient(event.clinic_id,event.patient_id);key=(event.clinic_id,event.follow_up_id)
        if key in self.followups:raise ImmutableRecordError("follow-up already exists")
        self.followups[key]=deepcopy(event);return deepcopy(event)

    def complete_followup(self,clinic_id:str,follow_up_id:str,user_id:str)->FollowupEvent:
        key=(clinic_id,follow_up_id);old=self.followups.get(key)
        if not old:
            if any(fid==follow_up_id for _,fid in self.followups):raise TenantAccessError("cross-clinic follow-up access denied")
            raise NotFoundError("follow-up not found")
        updated=old.model_copy(update={"status":"COMPLETED","completed_at":datetime.now(UTC),"completed_by":user_id})
        self.followups[key]=updated;return deepcopy(updated)

    def timeline(self,clinic_id:str,patient_id:str)->list[dict]:
        self.get_patient(clinic_id,patient_id);studies=sorted((s for (c,_),s in self.studies.items() if c==clinic_id and s.patient_id==patient_id),key=lambda s:(s.study_date or s.created_at.date(),s.created_at))
        return [{"study":deepcopy(s),"analyses":[deepcopy(a) for (c,_),a in self.analyses.items() if c==clinic_id and a.study_id==s.study_id]} for s in studies]

    def tooth_history(self,clinic_id:str,patient_id:str,fdi:str)->list[dict]:
        rows=[]
        for item in self.timeline(clinic_id,patient_id):
            for analysis in item["analyses"]:
                tooth=next((t for t in analysis.raw_ai_output.get("teeth",[]) if str(t.get("fdi"))==str(fdi)),None)
                if tooth:rows.append({"study_id":item["study"].study_id,"study_date":item["study"].study_date,"analysis_id":analysis.analysis_id,"fdi":str(fdi),"findings":deepcopy(tooth.get("final_findings",[])),"status":deepcopy(tooth.get("status_v2",{})),"restorations":deepcopy(tooth.get("restorations",[]))})
        return rows
