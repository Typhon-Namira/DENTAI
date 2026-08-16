import json
import unittest
from copy import deepcopy
from datetime import date
from pathlib import Path

from ai_engine.product.identity_v2 import decide_identity_state
from ai_engine.product.models import ExtractedField,ExtractedIdentity,PatientMatch,ProductIdentityState
from ai_engine.product.services_v2 import ProductIntelligenceService
from ai_engine.product.store import ImmutableRecordError,TenantAccessError

AI=json.loads(Path("artifacts/unified/dentai_unified_v5_onnx.json").read_text())

def identity(pid=None,name=None,dob=None,confidence=1.0):
    return ExtractedIdentity(
        patient_id=ExtractedField(value=pid,source="OCR",confidence=confidence) if pid else None,
        patient_name=ExtractedField(value=name,source="OCR",confidence=confidence) if name else None,
        date_of_birth=ExtractedField(value=dob,source="OCR",confidence=confidence) if dob else None,
    )

def image_ref(key):return {"storage_provider":"TEST","storage_bucket":"synthetic","storage_key":key,"sha256":"0"*64,"mime_type":"image/jpeg","size_bytes":1}

class ProductV2Tests(unittest.TestCase):
    def setUp(self):
        self.service=ProductIntelligenceService()
        self.service.create_patient(clinic_id="CLINIC-A",patient_id="PATIENT-001",display_name="Synthetic Patient One",clinic_local_identifier="A-001",date_of_birth=date(1980,1,2))

    def test_01_no_identity(self):
        state,matches=self.service.match_identity("CLINIC-A",identity())
        self.assertEqual(state,ProductIdentityState.IDENTITY_NOT_FOUND);self.assertFalse(matches)

    def test_02_exact_patient_id(self):
        state,matches=self.service.match_identity("CLINIC-A",identity(pid="A-001"))
        self.assertEqual(state,ProductIdentityState.IDENTITY_MATCHED_EXISTING);self.assertEqual(matches[0].patient_id,"PATIENT-001")

    def test_03_exact_id_and_name(self):
        state,_=self.service.match_identity("CLINIC-A",identity(pid="A-001",name="Synthetic Patient One"))
        self.assertEqual(state,ProductIdentityState.IDENTITY_MATCHED_EXISTING)

    def test_04_name_only_requires_review(self):
        state,_=self.service.match_identity("CLINIC-A",identity(name="Synthetic Patient One"))
        self.assertEqual(state,ProductIdentityState.IDENTITY_REVIEW_REQUIRED)

    def test_05_duplicate_names_are_ambiguous(self):
        self.service.create_patient(clinic_id="CLINIC-A",patient_id="PATIENT-002",display_name="Synthetic Patient One",clinic_local_identifier="A-002")
        state,matches=self.service.match_identity("CLINIC-A",identity(name="Synthetic Patient One"))
        self.assertEqual(state,ProductIdentityState.IDENTITY_REVIEW_REQUIRED);self.assertEqual(len(matches),2)

    def test_06_ambiguous_identity_state(self):
        matches=[PatientMatch(patient_id="A",match_score=.8,match_reasons=["NAME"]),PatientMatch(patient_id="B",match_score=.75,match_reasons=["NAME"])]
        self.assertEqual(decide_identity_state(identity(name="Synthetic"),matches),ProductIdentityState.IDENTITY_REVIEW_REQUIRED)

    def test_07_existing_patient_auto_association_strong_id_only(self):
        study,_=self.service.create_study(clinic_id="CLINIC-A",image_reference=image_ref("one"),identity=identity(pid="A-001"),study_date=date(2026,8,1))
        self.assertEqual(study.patient_id,"PATIENT-001")

    def test_08_new_patient_candidate_not_created(self):
        study,_=self.service.create_study(clinic_id="CLINIC-A",image_reference=image_ref("new"),identity=identity(pid="UNKNOWN-99"),study_date=date(2026,8,1))
        self.assertEqual(study.identity_state,ProductIdentityState.IDENTITY_NEW_PATIENT_CANDIDATE);self.assertIsNone(study.patient_id);self.assertEqual(len(self.service.store.patients),1)

    def test_09_identity_mismatch_requires_review(self):
        state,_=self.service.match_identity("CLINIC-A",identity(pid="A-001",name="Different Synthetic Person"))
        self.assertEqual(state,ProductIdentityState.IDENTITY_REVIEW_REQUIRED)

    def test_10_multiple_opgs_append_only(self):
        for n,day in ((1,date(2026,8,1)),(2,date(2026,11,1))):
            study,_=self.service.create_study(clinic_id="CLINIC-A",image_reference=image_ref(str(n)),identity=identity(pid="A-001"),study_date=day,study_id=f"STUDY-{n}")
            self.service.analyze(clinic_id="CLINIC-A",study_id=study.study_id,raw_ai_output=AI,analysis_date=day)
        timeline=self.service.store.timeline("CLINIC-A","PATIENT-001");self.assertEqual([x["study"].study_id for x in timeline],["STUDY-1","STUDY-2"])
        with self.assertRaises(ImmutableRecordError):self.service.create_study(clinic_id="CLINIC-A",image_reference=image_ref("replace"),identity=identity(pid="A-001"),study_id="STUDY-1")

    def test_11_cross_clinic_same_name_isolated(self):
        self.service.create_patient(clinic_id="CLINIC-B",patient_id="PATIENT-B",display_name="Synthetic Patient One",clinic_local_identifier="B-001")
        state,matches=self.service.match_identity("CLINIC-A",identity(pid="B-001",name="Synthetic Patient One"))
        self.assertNotEqual(state,ProductIdentityState.IDENTITY_MATCHED_EXISTING);self.assertNotIn("PATIENT-B",[x.patient_id for x in matches])
        with self.assertRaises(TenantAccessError):self.service.store.get_patient("CLINIC-A","PATIENT-B")

    def test_12_doctor_correction_audit_learning_and_ai_immutable(self):
        study,_=self.service.create_study(clinic_id="CLINIC-A",image_reference=image_ref("review"),identity=identity(pid="A-001"),study_date=date(2026,8,1))
        analysis=self.service.analyze(clinic_id="CLINIC-A",study_id=study.study_id,raw_ai_output=AI,analysis_date=date(2026,8,1));before=deepcopy(analysis.raw_ai_output)
        review=self.service.doctor_review(clinic_id="CLINIC-A",analysis_id=analysis.analysis_id,doctor_id="DOCTOR-1",action="MODIFY_STATUS",tooth_fdi="36",corrected_value="HEALTHY")
        self.assertEqual(review.corrected_value,"HEALTHY");self.assertEqual(self.service.store.analyses[("CLINIC-A",analysis.analysis_id)].raw_ai_output,before)
        self.assertTrue(any(x.action=="DOCTOR_REVIEWED" for x in self.service.store.audits));self.assertEqual(self.service.store.learning[-1].correction_payload["corrected_value"],"HEALTHY");self.assertFalse(self.service.store.learning[-1].training_eligibility)

    def test_13_followup_completion(self):
        study,_=self.service.create_study(clinic_id="CLINIC-A",image_reference=image_ref("follow"),identity=identity(pid="A-001"),study_date=date(2026,8,1));self.service.analyze(clinic_id="CLINIC-A",study_id=study.study_id,raw_ai_output=AI,analysis_date=date(2026,8,1))
        event=next(iter(self.service.store.followups.values()));done=self.service.complete_followup("CLINIC-A",event.follow_up_id,"DOCTOR-1")
        self.assertEqual(done.status,"COMPLETED");self.assertTrue(any(x.action=="FOLLOWUP_COMPLETED" for x in self.service.store.audits))

    def test_14_longitudinal_tooth_history(self):
        for n in (1,2):
            study,_=self.service.create_study(clinic_id="CLINIC-A",image_reference=image_ref(str(n)),identity=identity(pid="A-001"),study_date=date(2026,n+7,1));self.service.analyze(clinic_id="CLINIC-A",study_id=study.study_id,raw_ai_output=AI,analysis_date=study.study_date)
        history=self.service.store.tooth_history("CLINIC-A","PATIENT-001","36");self.assertEqual(len(history),2);self.assertEqual(history[0]["fdi"],"36")

    def test_15_image_111_product_regression(self):
        case=json.loads(Path("artifacts/product/sample_case_111.json").read_text());self.assertEqual(case["identity_status"],"IDENTITY_NOT_FOUND");self.assertIsNone(case["patient"]);self.assertEqual(len(case["overlay"]["teeth"]),32);self.assertEqual(case["analysis"]["raw_ai_output"]["teeth"],AI["teeth"])

    def test_16_ai_parity_artifact_remains_pass(self):
        parity=json.loads(Path("artifacts/evaluation/dentai_v5_onnx_parity.json").read_text());self.assertEqual(parity["parity_verdict"],"PASS");self.assertEqual(parity["acceptance_image_111"]["per_tooth_disagreements"],[])
        self.assertTrue(all(v["prediction_agreement"]==1 for v in parity["classifiers"].values()));self.assertEqual(parity["held_out_unified"]["final_finding_agreement"],1);self.assertEqual(parity["held_out_unified"]["review_flag_agreement"],1)

if __name__=="__main__":unittest.main()
