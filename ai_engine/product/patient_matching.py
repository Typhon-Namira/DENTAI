"""Candidate-only patient matching and confirmation workflow."""
import re,secrets,time,unicodedata
from .models import *
CROCK="0123456789ABCDEFGHJKMNPQRSTVWXYZ"
def new_id(prefix:str)->str:
 n=(int(time.time()*1000)<<80)|secrets.randbits(80);chars=[]
 for _ in range(26):chars.append(CROCK[n&31]);n>>=5
 return prefix+'-'+''.join(reversed(chars))
def new_patient_id():return new_id('PAT')
def normalize_text(v):
 value=unicodedata.normalize('NFKD',str(v or '')).encode('ascii','ignore').decode().casefold()
 return re.sub(r'[^a-z0-9]','',value)
def rank_patient_matches(clinic_id:str,identity:ExtractedIdentity,patients:list[Patient])->list[PatientMatch]:
 out=[];pid=normalize_text(identity.patient_id.value if identity.patient_id else None);name=normalize_text(identity.patient_name.value if identity.patient_name else None);dob=normalize_text(identity.date_of_birth.value if identity.date_of_birth else None)
 for p in patients:
  if p.clinic_id!=clinic_id:continue
  score=0.;reasons=[]
  if pid and pid==normalize_text(p.clinic_patient_number):score=max(score,.99);reasons.append('EXACT_CLINIC_PATIENT_ID')
  if pid and pid==normalize_text(p.dicom_patient_id):score=max(score,.97);reasons.append('EXACT_DICOM_PATIENT_ID')
  if pid and pid==normalize_text(p.external_patient_id):score=max(score,.95);reasons.append('EXACT_EXTERNAL_PATIENT_ID')
  if name and name==normalize_text(p.full_name):score+=.55;reasons.append('MATCHING_NORMALIZED_NAME')
  if dob and p.date_of_birth and dob==normalize_text(p.date_of_birth):score+=.35;reasons.append('MATCHING_DATE_OF_BIRTH')
  if reasons:out.append(PatientMatch(patient_id=p.patient_id,match_score=min(score,1),match_reasons=reasons))
 return sorted(out,key=lambda x:x.match_score,reverse=True)
def build_resolution(clinic_id,extraction,patients):
 matches=rank_patient_matches(clinic_id,extraction.extracted_identity,patients);conflict=len(matches)>1 and matches[0].match_score-matches[1].match_score<.1
 status=IdentityStatus.IDENTITY_CONFLICT if conflict else extraction.status
 return extraction.model_copy(update={'status':status,'candidate_patient_matches':matches,'conflict_reasons':['AMBIGUOUS_PATIENT_MATCHES']if conflict else[]})
def confirm_identity(resolution:IdentityResolution,action:IdentityAction,clinic_id:str,existing:Patient|None=None,corrections:dict|None=None):
 if action==IdentityAction.SELECT_EXISTING_PATIENT and not existing:raise ValueError('existing patient required')
 if action in(IdentityAction.CONFIRM,IdentityAction.CORRECT)and resolution.status==IdentityStatus.IDENTITY_NOT_FOUND:raise ValueError('no extracted identity to confirm')
 identity=resolution.extracted_identity
 if action==IdentityAction.CORRECT:
  updates={k:ExtractedField(value=str(v),source='OPERATOR',confidence=1.0,verified=True) for k,v in (corrections or {}).items() if k in ExtractedIdentity.model_fields and k!='metadata'}
  if not updates:raise ValueError('corrections required')
  identity=identity.model_copy(update=updates)
 elif action==IdentityAction.CONFIRM:
  updates={k:v.model_copy(update={'verified':True}) for k in ExtractedIdentity.model_fields if k!='metadata' and (v:=getattr(identity,k,None)) is not None}
  identity=identity.model_copy(update=updates)
 return resolution.model_copy(update={'status':IdentityStatus.IDENTITY_CONFIRMED,'extracted_identity':identity,'requires_confirmation':False,'confidence':1.0}),existing
def require_clinic(record,clinic_id):
 if getattr(record,'clinic_id',None)!=clinic_id:raise PermissionError('cross-tenant access denied')
 return record
