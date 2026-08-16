"""PHI-separated Learning Vault eligibility abstraction."""
from .models import LearningRecord,LabelState
from .patient_matching import new_id
def create_learning_record(clinic_id,source_case_id,model_version,verification_status=LabelState.AI_PRELABELED,deidentification_status='PENDING',consent_or_policy_reference=None):
 eligible=LabelState(verification_status)==LabelState.TRAIN_READY and deidentification_status=='COMPLETE'and bool(consent_or_policy_reference)
 return LearningRecord(learning_record_id=new_id('LRN'),clinic_id=clinic_id,source_case_id=source_case_id,source_model_version=model_version,verification_status=verification_status,deidentification_status=deidentification_status,training_eligibility=eligible,consent_or_policy_reference=consent_or_policy_reference)
def assert_no_direct_identity(record):
 dumped=record.model_dump();forbidden={'patient_name','first_name','last_name','date_of_birth','phone','email','dicom_patient_id'}
 if forbidden&set(dumped):raise ValueError('direct identity prohibited in Learning Vault')
 return True
