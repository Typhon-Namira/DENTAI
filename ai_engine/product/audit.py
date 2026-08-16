"""Append-only audit event construction. Persistence must reject updates/deletes."""
from .models import AuditEvent
from .patient_matching import new_id

AUDITED_ACTIONS={
    "IDENTITY_CONFIRMED","IDENTITY_CHANGED","AI_ANALYSIS_RUN","DOCTOR_REVIEWED",
    "FOLLOWUP_CHANGED","REMINDER_SCHEDULED","RECORD_EXPORTED","RECORD_DELETED",
    "LEARNING_ELIGIBILITY_CHANGED","PATIENT_CREATED","STUDY_CREATED","STUDY_ASSIGNED",
    "FOLLOWUP_CREATED","FOLLOWUP_COMPLETED","IDENTITY_REJECTED",
}

def audit_event(*,clinic_id:str,action:str,entity_type:str,entity_id:str,**context)->AuditEvent:
    if action not in AUDITED_ACTIONS:
        raise ValueError(f"unregistered audited action: {action}")
    return AuditEvent(audit_id=new_id("AUD"),clinic_id=clinic_id,action=action,
                      entity_type=entity_type,entity_id=entity_id,**context)
