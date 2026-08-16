"""Non-destructive de-identification preparation abstractions."""
from copy import deepcopy
DIRECT={'PatientName','PatientID','PatientBirthDate','PatientAddress','PatientTelephoneNumbers','OtherPatientIDs','AccessionNumber'}
def scrub_dicom_metadata(metadata,replacement_patient_id):
 out=deepcopy(metadata)
 for key in DIRECT:out.pop(key,None)
 out['PatientID']=replacement_patient_id;return out
def prepare_training_derivative(source_reference,derivative_reference,burned_in_text_regions=None):
 if source_reference==derivative_reference:raise ValueError('clinical original must not be overwritten')
 return {'source_clinical_asset_reference':source_reference,'deidentified_derivative_reference':derivative_reference,'dicom_phi_removal_required':True,'burned_in_text_redaction_required':bool(burned_in_text_regions),'redaction_regions':burned_in_text_regions or[],'status':'PENDING','contains_direct_identity':False}
