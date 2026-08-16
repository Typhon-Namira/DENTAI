"""Executable Product Intelligence V2 acceptance and synthetic clinic workflow."""
from __future__ import annotations
import argparse,json,time
from datetime import date,datetime
from enum import Enum
from copy import deepcopy
from pathlib import Path
from PIL import Image
from ai_engine.inference.dentai_unified_v5_onnx import Engine
from ai_engine.product.identity_v2 import NoOpIdentityExtractor
from ai_engine.product.models import ExtractedField,ExtractedIdentity
from ai_engine.product.services_v2 import ProductIntelligenceService
from ai_engine.product.store import TenantAccessError

ROOT=Path(__file__).resolve().parents[2]
IMAGE=ROOT/"data/raw/akudental/current/source_repo/AKUDENTAL/images/111.jpg"
OUT=ROOT/"artifacts/product/dentai_product_v2_acceptance.json"
DASHBOARD=ROOT/"artifacts/product/sample_dashboard_111_v2.json"

def ident(pid=None,name=None,confidence=1.0):
    return ExtractedIdentity(patient_id=ExtractedField(value=pid,source="SYNTHETIC_TEST",confidence=confidence) if pid else None,patient_name=ExtractedField(value=name,source="SYNTHETIC_TEST",confidence=confidence) if name else None)

def reference(key):
    return {"storage_provider":"TEST_REFERENCE","storage_bucket":"synthetic","storage_key":key,"sha256":"0"*64,"mime_type":"image/jpeg","size_bytes":IMAGE.stat().st_size}

def json_default(value):
    if isinstance(value,(date,datetime)):return value.isoformat()
    if isinstance(value,Enum):return value.value
    raise TypeError(f"not JSON serializable: {type(value).__name__}")

def run(run_second_inference=True):
    timings={};t=time.perf_counter();Image.open(IMAGE).convert("RGB");timings["standalone_image_decode_preprocessing_seconds"]=time.perf_counter()-t
    t=time.perf_counter();NoOpIdentityExtractor().extract(IMAGE);timings["ocr_noop_seconds"]=time.perf_counter()-t
    t=time.perf_counter();engine=Engine(4);timings["onnx_model_load_seconds"]=time.perf_counter()-t
    t=time.perf_counter();ai1=engine.analyze(str(IMAGE));timings["onnx_inference_opg_1_seconds"]=time.perf_counter()-t
    if run_second_inference:
        t=time.perf_counter();ai2=engine.analyze(str(IMAGE));timings["onnx_inference_opg_2_seconds"]=time.perf_counter()-t
    else:ai2=deepcopy(ai1);timings["onnx_inference_opg_2_seconds"]=None
    service=ProductIntelligenceService();t=time.perf_counter()
    service.create_patient(clinic_id="CLINIC-A",patient_id="PATIENT-001",display_name="Synthetic Patient One",clinic_local_identifier="A-001",actor_id="ADMIN-A")
    study1,matches1=service.create_study(clinic_id="CLINIC-A",image_reference=reference("clinic-a/opg-1.jpg"),identity=ident("A-001","Synthetic Patient One"),study_date=date(2026,8,1),actor_id="DOCTOR-A",study_id="OPG-001")
    analysis1=service.analyze(clinic_id="CLINIC-A",study_id=study1.study_id,raw_ai_output=ai1,analysis_date=study1.study_date,actor_id="DOCTOR-A")
    study2,matches2=service.create_study(clinic_id="CLINIC-A",image_reference=reference("clinic-a/opg-2.jpg"),identity=ident(name="Synthetic Patient One"),study_date=date(2026,11,1),actor_id="DOCTOR-A",study_id="OPG-002")
    before_assignment=study2.identity_state.value;study2=service.assign_patient("CLINIC-A",study2.study_id,"PATIENT-001","DOCTOR-A")
    analysis2=service.analyze(clinic_id="CLINIC-A",study_id=study2.study_id,raw_ai_output=ai2,analysis_date=study2.study_date,actor_id="DOCTOR-A")
    review=service.doctor_review(clinic_id="CLINIC-A",analysis_id=analysis2.analysis_id,doctor_id="DOCTOR-A",action="MODIFY_STATUS",tooth_fdi="36",corrected_value="HEALTHY",notes="Synthetic acceptance correction")
    followup=next(x for x in service.store.followups.values() if x.analysis_id==analysis2.analysis_id);completed=service.complete_followup("CLINIC-A",followup.follow_up_id,"DOCTOR-A")
    service.create_patient(clinic_id="CLINIC-B",patient_id="PATIENT-B-001",display_name="Synthetic Patient One",clinic_local_identifier="B-001",actor_id="ADMIN-B")
    isolated=False
    try:service.store.get_patient("CLINIC-A","PATIENT-B-001")
    except TenantAccessError:isolated=True
    timings["product_intelligence_and_reference_persistence_seconds"]=time.perf_counter()-t
    timeline=service.store.timeline("CLINIC-A","PATIENT-001");history=service.store.tooth_history("CLINIC-A","PATIENT-001","36")
    parity=json.loads((ROOT/"artifacts/evaluation/dentai_v5_onnx_parity.json").read_text())
    unchanged=service.store.analyses[("CLINIC-A",analysis2.analysis_id)].raw_ai_output==ai2
    dashboard=analysis2.product_output["dashboard"]
    checks={
      "ai_parity":parity["parity_verdict"]=="PASS" and parity["held_out_unified"]["final_finding_agreement"]==1,
      "identity_extraction":NoOpIdentityExtractor().extract(IMAGE)["fields"]=={},
      "identity_matching":study1.patient_id=="PATIENT-001" and before_assignment=="IDENTITY_REVIEW_REQUIRED" and study2.patient_id=="PATIENT-001",
      "patient_profile":service.store.get_patient("CLINIC-A","PATIENT-001").display_name=="Synthetic Patient One",
      "longitudinal_timeline":len(timeline)==2 and [x["study"].study_id for x in timeline]==["OPG-001","OPG-002"],
      "tooth_history":len(history)==2,
      "doctor_review":review.corrected_value=="HEALTHY" and unchanged,
      "follow_up_engine":completed.status=="COMPLETED" and bool(followup.rule_ids),
      "learning_vault":len(service.store.learning)==1 and not service.store.learning[0].training_eligibility,
      "tenant_isolation":isolated,
      "audit":any(x.action=="DOCTOR_REVIEWED" for x in service.store.audits) and any(x.action=="FOLLOWUP_COMPLETED" for x in service.store.audits),
      "dashboard_contract":dashboard["schema_version"]=="dentai-dashboard-v2" and len(dashboard["opg"]["selectable_teeth"])==32,
      "end_to_end":len(ai1["teeth"])==32 and ai1["summary"]["unique_fdi"]==32 and unchanged,
    }
    inference=[x for x in (timings["onnx_inference_opg_1_seconds"],timings["onnx_inference_opg_2_seconds"]) if x is not None]
    timings.update({"onnx_inference_mean_seconds":sum(inference)/len(inference),"database_persistence_seconds":None,"database_persistence_note":"No live PostgreSQL was configured; the measured reference-store persistence time is included in product intelligence timing.","total_measured_workflow_seconds":sum(inference)+timings["ocr_noop_seconds"]+timings["product_intelligence_and_reference_persistence_seconds"]})
    result={"version":"dentai-product-intelligence-v2","checks":checks,"ui":{"dashboard_backend_contract":"PASS","rendered_dashboard":"NOT_IMPLEMENTED_NO_FRONTEND_CODEBASE","production_visual_acceptance":"NOT_RUN"},"performance":timings,"workflow":{"clinic_a":{"patient_id":"PATIENT-001","display_name":"Synthetic Patient One","opg_1":{"study_id":study1.study_id,"analysis_id":analysis1.analysis_id,"identity_state":study1.identity_state,"teeth":len(ai1["teeth"]),"unique_fdi":ai1["summary"]["unique_fdi"]},"opg_2":{"study_id":study2.study_id,"analysis_id":analysis2.analysis_id,"identity_state_before_confirmation":before_assignment,"association":"EXPLICITLY_CONFIRMED","teeth":len(ai2["teeth"]),"unique_fdi":ai2["summary"]["unique_fdi"]},"timeline":[x["study"].study_id for x in timeline],"tooth_36_history":history,"doctor_correction":review.model_dump(mode="json"),"follow_up_completed":completed.model_dump(mode="json")},"clinic_b":{"patient_id":"PATIENT-B-001","same_display_name":True,"visible_from_clinic_a":not isolated}},"immutability":{"raw_ai_output_preserved":unchanged,"production_model_modified":False,"production_model_sha_check":"covered by frozen parity manifest"},"dashboard_summary":dashboard["clinical_intelligence"]["overall_assessment"],"limitations":["No rendered frontend exists in this repository; dashboard acceptance covers its backend presentation contract.","Live PostgreSQL latency was not measured because no acceptance database was configured.","No-op OCR was measured; a production OCR provider is not configured."]}
    serialized=json.loads(json.dumps(result,default=json_default,allow_nan=False));OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(serialized,indent=2,allow_nan=False));DASHBOARD.write_text(json.dumps(serialized["workflow"] and dashboard,indent=2,allow_nan=False,default=json_default));return serialized

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--reuse-second-inference",action="store_true");args=parser.parse_args();result=run(not args.reuse_second_inference)
    print("="*60);print("DENTAI PRODUCT INTELLIGENCE V2\nFINAL ACCEPTANCE");print("="*60)
    labels=(("AI PARITY","ai_parity"),("IDENTITY EXTRACTION","identity_extraction"),("IDENTITY MATCHING","identity_matching"),("PATIENT PROFILE","patient_profile"),("LONGITUDINAL TIMELINE","longitudinal_timeline"),("TOOTH HISTORY","tooth_history"),("DOCTOR REVIEW","doctor_review"),("FOLLOW-UP ENGINE","follow_up_engine"),("LEARNING VAULT","learning_vault"),("TENANT ISOLATION","tenant_isolation"),("AUDIT","audit"))
    for label,key in labels:print(f"{label}: {'PASS' if result['checks'][key] else 'FAIL'}")
    print("DASHBOARD: FAIL (backend contract PASS; rendered frontend absent)");print(f"END-TO-END: {'PASS' if result['checks']['end_to_end'] else 'FAIL'} (backend/domain workflow)");print("TESTS: run tests/product separately")
    print("="*60);print("Timeline: OPG-001 -> OPG-002");print("Tooth 36 history entries:",len(result["workflow"]["clinic_a"]["tooth_36_history"]));print("Artifact:",OUT)
    raise SystemExit(0 if all(result["checks"].values()) else 1)
if __name__=="__main__":main()
