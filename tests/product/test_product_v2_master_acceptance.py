import json
import unittest
from pathlib import Path

class ProductV2MasterAcceptance(unittest.TestCase):
    def test_master_acceptance_artifacts_and_frozen_parity(self):
        result=json.loads(Path("artifacts/product/dentai_product_v2_acceptance.json").read_text(),parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
        self.assertTrue(all(result["checks"].values()))
        parity=json.loads(Path("artifacts/evaluation/dentai_v5_onnx_parity.json").read_text())
        self.assertEqual(parity["parity_verdict"],"PASS")
        for name in ("tooth","pathology","restoration_detector"):
            detector=parity["detectors"][name];self.assertEqual(detector["pytorch_detections"],detector["onnx_detections"]);self.assertEqual(detector["pytorch_detections"],detector["matched_iou_090"]);self.assertEqual(detector["class_agreement"],1)
        for classifier in parity["classifiers"].values():self.assertEqual(classifier["prediction_agreement"],1)
        unified=parity["held_out_unified"]
        for key in ("fdi_agreement","status_gate_agreement","status_v2_agreement","final_finding_agreement","review_flag_agreement"):self.assertEqual(unified[key],1)
        workflow=result["workflow"]["clinic_a"]
        self.assertEqual(workflow["timeline"],["OPG-001","OPG-002"]);self.assertEqual(workflow["opg_2"]["association"],"EXPLICITLY_CONFIRMED")
        self.assertTrue(result["immutability"]["raw_ai_output_preserved"]);self.assertFalse(result["immutability"]["production_model_modified"])
        self.assertFalse(result["workflow"]["clinic_b"]["visible_from_clinic_a"])
        sql=Path("database/schema/dentai_product_v2.sql").read_text()
        for table in ("identity_candidates","identity_reviews","product_intelligence_outputs","tooth_history_snapshots","follow_up_events","learning_vault_records"):self.assertIn(f"CREATE TABLE IF NOT EXISTS {table}",sql)
        dashboard=json.loads(Path("artifacts/product/sample_dashboard_111_v2.json").read_text());self.assertEqual(dashboard["schema_version"],"dentai-dashboard-v2");self.assertEqual(len(dashboard["opg"]["selectable_teeth"]),32);self.assertFalse(dashboard["opg"]["layer_toggles"]["DEBUG"])

if __name__=="__main__":unittest.main()
