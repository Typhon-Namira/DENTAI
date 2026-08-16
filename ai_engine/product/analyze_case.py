"""Product orchestration above immutable DENTAI ONNX V5 inference."""
import argparse,hashlib,json,mimetypes
from copy import deepcopy
from datetime import date
from pathlib import Path
from .models import DentaiCaseAnalysis,Study,IdentityStatus,utcnow
from .patient_identity import extract_identity,IdentityOCRProvider
from .patient_matching import build_resolution,new_id
from .risk_followup import FollowupEngine
from .opg_overlay import build_overlay,side_panel
from .longitudinal import compare_patient_exams
from .learning_vault import create_learning_record

MANIFEST=Path('artifacts/production/dentai_v5_model_manifest.json')
def file_sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def analyze_case(input_file,clinic_id,patients=None,confirmed_patient=None,previous_exam=None,ocr_provider:IdentityOCRProvider|None=None,inference_result=None,analysis_date=None):
 path=Path(input_file);ext=path.suffix.lower();source='DICOM'if ext in('.dcm','.dicom')else'PNG'if ext=='.png'else'JPG'
 identity=build_resolution(clinic_id,extract_identity(path,ocr_provider),patients or[])
 if confirmed_patient:identity=identity.model_copy(update={'status':IdentityStatus.IDENTITY_CONFIRMED,'requires_confirmation':False,'confidence':1.0})
 if inference_result is None:
  if source=='DICOM':raise NotImplementedError('DICOM pixel conversion must be supplied before ONNX inference; identity extraction is supported independently')
  from ai_engine.inference.dentai_unified_v5_onnx import Engine
  inference_result=Engine(4).analyze(str(path))
 manifest_hash=file_sha(MANIFEST);case_id=new_id('CASE');study_id=new_id('STD');analysis_id=new_id('ANL');day=analysis_date or date.today();engine=FollowupEngine();follow={}
 for tooth in inference_result['teeth']:follow[str(tooth['fdi'])]=engine.recommend(tooth,day).model_dump(mode='json')
 overlay=build_overlay(inference_result,follow);comparison=compare_patient_exams(previous_exam,overlay)if previous_exam else None
 levels=['URGENT_REVIEW','HIGH','MEDIUM','LOW','ROUTINE'];highest=min((x['risk_level']for x in follow.values()),key=levels.index,default='ROUTINE');targets=[x['target_followup_date']for x in follow.values()if x['risk_level']==highest]
 study=Study(study_id=study_id,clinic_id=clinic_id,patient_id=confirmed_patient.patient_id if confirmed_patient else None,source_type=source,study_date=day,storage_reference={'storage_provider':'UNASSIGNED','storage_bucket':None,'storage_key':str(path),'sha256':file_sha(path),'mime_type':mimetypes.guess_type(path)[0]or'application/octet-stream','size_bytes':path.stat().st_size})
 learning=create_learning_record(clinic_id,case_id,'dentai-unified-v5')
 product=DentaiCaseAnalysis(case_id=case_id,clinic_id=clinic_id,patient=({'patient_id':confirmed_patient.patient_id,'name':confirmed_patient.full_name,'verified':True}if confirmed_patient else None),identity_status=identity.status,identity=identity,study=study,model={'model_version':'dentai-unified-v5','runtime':'ONNX Runtime CPUExecutionProvider','model_manifest_hash':manifest_hash,'thresholds':inference_result['thresholds']},analysis={'analysis_id':analysis_id,'study_id':study_id,'model_version':'dentai-unified-v5','model_manifest_hash':manifest_hash,'thresholds':inference_result['thresholds'],'analysis_timestamp':utcnow(),'teeth':len(inference_result['teeth']),'original_ai_output_preserved':True,'raw_ai_output':deepcopy(inference_result)},overlay=overlay,tooth_results=[{**x,'side_panel':side_panel(x)}for x in overlay['teeth']],followup={'highest_risk':highest,'target_date':min(targets)if targets else None,'per_tooth':follow,'configurable_product_defaults':True,'doctor_override_supported':True},longitudinal_comparison=comparison,review_summary={'review_required_teeth':sum(x['review_required']for x in overlay['teeth']),'doctor_reviews':0,'predictions_immutable':True},learning_status={'state':learning.verification_status,'training_eligible':learning.training_eligibility,'contains_direct_patient_identity':False})
 return product
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--clinic-id',required=True);p.add_argument('--inference-json');p.add_argument('--output',required=True);p.add_argument('--overlay-output');a=p.parse_args();inf=json.loads(Path(a.inference_json).read_text())if a.inference_json else None;r=analyze_case(a.input,a.clinic_id,inference_result=inf);Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(r.model_dump_json(indent=2))
 if a.overlay_output:
  Path(a.overlay_output).parent.mkdir(parents=True,exist_ok=True);Path(a.overlay_output).write_text(json.dumps(r.overlay,indent=2,allow_nan=False))
 print('Case:',r.case_id,'Teeth:',len(r.tooth_results),'Identity:',r.identity_status,'Risk:',r.followup['highest_risk'],'Target:',r.followup['target_date'])
if __name__=='__main__':main()
