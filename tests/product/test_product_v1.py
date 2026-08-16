import json,unittest
from datetime import date
from pathlib import Path
from pydantic import ValidationError
from ai_engine.product.models import *
from ai_engine.product.patient_matching import *
from ai_engine.product.risk_followup import FollowupEngine
from ai_engine.product.longitudinal import compare_patient_exams
from ai_engine.product.doctor_review import create_review,transition_label
from ai_engine.product.learning_vault import create_learning_record,assert_no_direct_identity
from ai_engine.product.deidentification import scrub_dicom_metadata,prepare_training_derivative
from ai_engine.product.opg_overlay import build_overlay
from ai_engine.product.reminders import schedule_reminder
from ai_engine.product.patient_identity import extract_image_identity,IdentityOCRProvider

class ProductTests(unittest.TestCase):
 def patient(self,pid='PAT-A',clinic='CLINIC-A',name='Arman Hakobyan',dob=date(1980,1,2)):
  return Patient(patient_id=pid,clinic_id=clinic,full_name=name,date_of_birth=dob,dicom_patient_id='D-1')
 def test_patient_ids_unique(self):
  ids={new_patient_id()for _ in range(1000)};self.assertEqual(len(ids),1000);self.assertTrue(all(x.startswith('PAT-')for x in ids))
 def test_normalization(self):self.assertEqual(normalize_text(' Árman-HAKOBYAN '),normalize_text('arman hakobyan'))
 def test_ambiguous_matching(self):
  e=ExtractedIdentity(patient_name=ExtractedField(value='Arman Hakobyan',source='OCR',confidence=.7),date_of_birth=ExtractedField(value='1980-01-02',source='OCR',confidence=.7));x=IdentityResolution(status=IdentityStatus.IDENTITY_NEEDS_CONFIRMATION,extracted_identity=e)
  r=build_resolution('CLINIC-A',x,[self.patient(),self.patient('PAT-B')]);self.assertEqual(r.status,IdentityStatus.IDENTITY_CONFLICT);self.assertTrue(r.requires_confirmation)
 def test_identity_confirmation(self):
  e=ExtractedIdentity(patient_id=ExtractedField(value='D-1',source='DICOM',confidence=1));x=IdentityResolution(status=IdentityStatus.IDENTITY_NEEDS_CONFIRMATION,extracted_identity=e);r,_=confirm_identity(x,IdentityAction.CONFIRM,'CLINIC-A');self.assertEqual(r.status,IdentityStatus.IDENTITY_CONFIRMED)
  self.assertTrue(r.extracted_identity.patient_id.verified)
 def test_identity_correction(self):
  e=ExtractedIdentity(patient_name=ExtractedField(value='Wrong',source='OCR',confidence=.4));x=IdentityResolution(status=IdentityStatus.IDENTITY_NEEDS_CONFIRMATION,extracted_identity=e);r,_=confirm_identity(x,IdentityAction.CORRECT,'CLINIC-A',corrections={'patient_name':'Correct Name'});self.assertEqual(r.extracted_identity.patient_name.value,'Correct Name');self.assertTrue(r.extracted_identity.patient_name.verified)
 def test_ocr_identity_stays_unverified(self):
  class Stub(IdentityOCRProvider):
   def extract(self,image_path):return {'patient_name':('Candidate Name',.8)}
  r=extract_image_identity(Path('unused.jpg'),Stub());self.assertEqual(r.patient_name.source,'OCR');self.assertFalse(r.patient_name.verified)
 def test_tenant_isolation(self):
  with self.assertRaises(PermissionError):require_clinic(self.patient(),'CLINIC-B')
 def test_followup_and_override(self):
  e=FollowupEngine();r=e.recommend({'final_findings':['CARIES'],'review_required':False},date(2026,8,16));self.assertEqual(r.risk_level,RiskLevel.HIGH);self.assertEqual(str(r.target_followup_date),'2026-11-16');o=e.recommend({'final_findings':['CARIES'],'review_required':False},date(2026,8,16),{'risk_level':'LOW','target_date':'2027-01-01'});self.assertTrue(o.doctor_overridden);self.assertEqual(str(o.target_followup_date),'2027-01-01')
 def test_longitudinal_new_resolved(self):
  a={'teeth':[{'fdi':'36','final_findings':['CARIES']},{'fdi':'46','final_findings':['FILLING']}]};b={'teeth':[{'fdi':'36','final_findings':['DEEP_CARIES']},{'fdi':'46','final_findings':['HEALTHY']}]};r=compare_patient_exams(a,b);self.assertIn({'fdi':'36','finding':'DEEP_CARIES'},r['new_findings']);self.assertIn({'fdi':'46','finding':'FILLING'},r['resolved_findings'])
 def test_ai_prediction_immutable(self):
  original={'finding':'CARIES'};r=create_review('CLINIC-A','ANL-1','DOC-1',original,'CORRECT',corrected_value='HEALTHY');original['finding']='CHANGED';self.assertEqual(r.original_ai_output['finding'],'CARIES');
  with self.assertRaises(ValidationError):r.notes='mutate'
 def test_learning_transitions_and_no_phi(self):
  self.assertEqual(transition_label('VERIFIED','TRAIN_READY',True),LabelState.TRAIN_READY)
  with self.assertRaises(ValueError):transition_label('AI_PRELABELED','TRAIN_READY',True)
  r=create_learning_record('CLINIC-A','CASE-1','dentai-unified-v5');self.assertTrue(assert_no_direct_identity(r));self.assertFalse(r.training_eligibility)
 def test_deidentification(self):
  source={'PatientName':'A','PatientID':'1','Modality':'PX'};out=scrub_dicom_metadata(source,'DEID-1');self.assertNotIn('PatientName',out);self.assertEqual(source['PatientName'],'A');self.assertEqual(out['PatientID'],'DEID-1')
  with self.assertRaises(ValueError):prepare_training_derivative('same','same')
 def test_reminder_schema(self):
  from datetime import datetime,timezone
  r=schedule_reminder(clinic_id='CLINIC-A',patient_id='PAT-A',case_id='CASE-A',scheduled_at=datetime.now(timezone.utc),channel='IN_APP',reminder_type='FOLLOWUP',message_template='FOLLOWUP_DUE',created_by='DOC-A');self.assertEqual(r.clinic_id,'CLINIC-A')
  with self.assertRaises(ValueError):schedule_reminder(clinic_id='CLINIC-A',patient_id='PAT-A',case_id='CASE-A',scheduled_at=datetime.now(timezone.utc),channel='FAX',reminder_type='FOLLOWUP',message_template='X',created_by='DOC-A')
 def test_overlay_schema(self):
  p=Path('artifacts/unified/dentai_unified_v5_onnx.json');self.assertTrue(p.exists());ai=json.loads(p.read_text());o=build_overlay(ai);self.assertEqual(len(o['teeth']),len(ai['teeth']));self.assertIn('TOOTH_BOXES',o['layers']);self.assertEqual(o['coordinate_space'],'ORIGINAL_IMAGE_PIXELS')

if __name__=='__main__':unittest.main()
