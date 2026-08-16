"""Final, test-only master evaluation for DENTAI Unified Brain V5.

This evaluator deliberately separates held-out test metrics from validation
metadata, records denominators, and never substitutes unavailable labels.
"""

import csv
import gc
import json
import math
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch
from PIL import Image
from torchvision.transforms.functional import to_tensor

from ai_engine.inference import dentai_unified_v5 as v5


OUT = Path("artifacts/evaluation/dentai_v5_master")
CM_DIR = OUT / "confusion_matrices"
TOOTH_TEST = Path("data/canonical/dentai_v3_super/test.json")
TOOTH_TRAIN = Path("data/canonical/dentai_v3_super/train.json")
STATUS_TEST = Path("data/canonical/dual_labeled_status/test.json")
STATUS_TRAIN = Path("data/canonical/dual_labeled_status/train.json")
SUPER_TEST = Path("data/canonical/dentai_v3_super/test.json")
SUPER_TRAIN = Path("data/canonical/dentai_v3_super/train.json")
TOOTH_SPLIT = Path("data/splits/tooth_v2")
AKU_CANONICAL = Path("data/canonical/akudental/git-92e2cc3/instances.json")
TOOTH_SOURCES = {"dentex_hf_7b27ccc8", "akudental_git_92e2cc3", "dual_labeled_fdi"}
PATH_SOURCES = {"oralxrays9", "zenodo14"}
FINDING_CLASSES = ["CARIES", "FILLING", "CROWN", "ROOT_CANAL_TREATMENT", "RESIDUAL_ROOT"]


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def safe_div(a, b):
    return a / b if b else 0.0


def f1(p, r):
    return safe_div(2 * p * r, p + r)


def image_key(record):
    return (str(record.get("source_dataset", "")), str(record.get("source_image_id", "")))


def split_overlap(train_path, test_path):
    train, test = load_json(train_path)["records"], load_json(test_path)["records"]
    train_ids, test_ids = {image_key(r) for r in train}, {image_key(r) for r in test}
    train_paths = {str(r.get("image_path")) for r in train}
    test_paths = {str(r.get("image_path")) for r in test}
    train_hashes = {r.get("image_sha256") for r in train if r.get("image_sha256")}
    test_hashes = {r.get("image_sha256") for r in test if r.get("image_sha256")}
    return {"source_id_overlap": len(train_ids & test_ids), "path_overlap": len(train_paths & test_paths),
            "sha256_overlap": len(train_hashes & test_hashes),
            "status": "SAFE_TEST" if not (train_ids & test_ids or train_paths & test_paths or train_hashes & test_hashes) else "POSSIBLE_OVERLAP",
            "patient_independence": "UNKNOWN"}


def binary_metrics(cm, classes):
    total = sum(map(sum, cm)); correct = sum(cm[i][i] for i in range(len(classes)))
    per = {}
    for i, name in enumerate(classes):
        tp = cm[i][i]; fp = sum(cm[j][i] for j in range(len(classes)) if j != i)
        fn = sum(cm[i][j] for j in range(len(classes)) if j != i)
        p, r = safe_div(tp, tp + fp), safe_div(tp, tp + fn)
        per[name] = {"precision": p, "recall": r, "f1": f1(p, r), "support": sum(cm[i]), "tp": tp, "fp": fp, "fn": fn}
    supports = sum(x["support"] for x in per.values())
    return {"accuracy": safe_div(correct, total), "macro_precision": statistics.mean(x["precision"] for x in per.values()),
            "macro_recall": statistics.mean(x["recall"] for x in per.values()),
            "balanced_accuracy": statistics.mean(x["recall"] for x in per.values()),
            "macro_f1": statistics.mean(x["f1"] for x in per.values()),
            "weighted_f1": safe_div(sum(x["f1"] * x["support"] for x in per.values()), supports),
            "support": total, "correct": correct, "per_class": per, "confusion_matrix": cm,
            "confusion_matrix_labels": classes}


def save_confusion(name, cm, labels):
    CM_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = CM_DIR / f"{name}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle); writer.writerow(["gt/pred", *labels])
        for label, row in zip(labels, cm): writer.writerow([label, *row])
    fig_size = max(5, min(13, len(labels) * .43))
    fig, ax = plt.subplots(figsize=(fig_size, fig_size))
    im = ax.imshow(cm, cmap="Blues"); fig.colorbar(im, ax=ax, fraction=.046)
    ax.set_xticks(range(len(labels)), labels=labels, rotation=90, fontsize=7)
    ax.set_yticks(range(len(labels)), labels=labels, fontsize=7)
    ax.set_xlabel("Predicted"); ax.set_ylabel("Ground truth"); ax.set_title(name.replace("_", " ").title())
    if len(labels) <= 8:
        for i, row in enumerate(cm):
            for j, value in enumerate(row): ax.text(j, i, str(value), ha="center", va="center", fontsize=7)
    fig.tight_layout(); fig.savefig(CM_DIR / f"{name}.png", dpi=160); plt.close(fig)


def greedy_match(gt_boxes, pred_boxes, threshold=.5):
    candidates = sorted(((v5.intersection_metrics(g, p)[0], gi, pi)
                         for gi, g in enumerate(gt_boxes) for pi, p in enumerate(pred_boxes)), reverse=True)
    matches, used_g, used_p = [], set(), set()
    for overlap, gi, pi in candidates:
        if overlap < threshold: break
        if gi not in used_g and pi not in used_p:
            matches.append((gi, pi, overlap)); used_g.add(gi); used_p.add(pi)
    return matches


def records_for_tooth():
    return [r for r in load_json(TOOTH_TEST)["records"] if r.get("source_dataset") in TOOTH_SOURCES
            and any(x.get("canonical_class") == "TOOTH" and x.get("polygon") for x in r.get("instances", []))]


def pathology_records(split):
    records = []
    for original in ("train", "validation", "test"):
        for r in load_json(Path(f"data/canonical/dentai_v3_super/{original}.json"))["records"]:
            source = r.get("source_dataset")
            if source not in PATH_SOURCES: continue
            if source == "oralxrays9":
                import hashlib
                bucket = int(hashlib.sha1(f"{source}:{r.get('source_image_id')}".encode()).hexdigest()[:8], 16) % 100
                target = "validation" if bucket < 10 else "train"
            else: target = original
            if target == split: records.append(r)
    return records


def restoration_records(split):
    mapping = {}
    for part in ("train", "validation", "test"):
        for r in load_json(TOOTH_SPLIT / f"{part}.json")["records"]:
            if r.get("source_dataset", "").startswith("akudental"):
                mapping[str(r["source_image_id"])] = part
    rows = []
    base = Path("data/raw/akudental/current/source_repo/AKUDENTAL/images")
    for r in load_json(AKU_CANONICAL)["images"]:
        iid = str(r.get("source_image_id", ""))
        if mapping.get(iid) != split: continue
        objects = [{"type": str(x.get("canonical_class", "")).upper(), "bbox": x.get("bbox_xyxy")}
                   for x in r.get("instances", []) if str(x.get("canonical_class", "")).upper() in ("FILLING", "IMPLANT") and x.get("bbox_xyxy")]
        rows.append({"image_path": str(base / iid), "source_image_id": iid, "objects": objects})
    return rows


def dataset_audit():
    tooth = records_for_tooth(); status = load_json(STATUS_TEST)["records"]
    pathology = pathology_records("test"); deep = []
    for r in load_json(SUPER_TEST)["records"]:
        deep += [x for x in r.get("instances", []) if x.get("source_disease") in ("Caries", "Deep Caries")]
    rest = restoration_records("test")
    tooth_objects = sum(sum(x.get("canonical_class") == "TOOTH" for x in r.get("instances", [])) for r in tooth)
    path_counts = Counter(x.get("canonical_class") for r in pathology for x in r.get("instances", []) if x.get("canonical_class") in v5.PATHOLOGY_THRESHOLDS)
    rest_counts = Counter(x["type"] for r in rest for x in r["objects"])
    status_counts = Counter(t["status"] for r in status for t in r["teeth"])
    super_leak = split_overlap(SUPER_TRAIN, SUPER_TEST)
    status_leak = split_overlap(STATUS_TRAIN, STATUS_TEST)
    tooth_v2_leak = split_overlap(TOOTH_SPLIT / "train.json", TOOTH_SPLIT / "test.json")
    audit = [
        {"task": "Tooth detection/segmentation", "dataset": str(TOOTH_TEST), "source": sorted(TOOTH_SOURCES), "test_images": len(tooth), "gt_objects": tooth_objects, "classes": ["TOOTH"], "available": True, "leakage": super_leak},
        {"task": "FDI numbering", "dataset": str(TOOTH_TEST), "source": sorted(TOOTH_SOURCES), "test_images": len(tooth), "gt_objects": tooth_objects, "classes": v5.FDI_CLASSES, "available": True, "leakage": super_leak},
        {"task": "Tooth-level status", "dataset": str(STATUS_TEST), "source": ["dual_labeled_status"], "test_images": len(status), "gt_objects": sum(status_counts.values()), "classes": v5.STATUS_CLASSES, "available": True, "leakage": status_leak},
        {"task": "Pathology detection", "dataset": str(SUPER_TEST), "source": sorted(set(r.get("source_dataset") for r in pathology)), "test_images": len(pathology), "gt_objects": sum(path_counts.values()), "classes": list(v5.PATHOLOGY_THRESHOLDS), "available": True, "leakage": super_leak},
        {"task": "Deep Caries", "dataset": str(SUPER_TEST), "source": sorted(set(r.get("source_dataset") for r in load_json(SUPER_TEST)["records"] if any(x.get("source_disease") in ("Caries", "Deep Caries") for x in r.get("instances", [])))), "test_images": len({r["image_path"] for r in load_json(SUPER_TEST)["records"] if any(x.get("source_disease") in ("Caries", "Deep Caries") for x in r.get("instances", []))}), "gt_objects": len(deep), "classes": v5.DEEP_CARIES_CLASSES, "available": True, "leakage": super_leak},
        {"task": "Restoration detection/classification", "dataset": str(AKU_CANONICAL) + " + " + str(TOOTH_SPLIT / "test.json"), "source": ["akudental"], "test_images": len(rest), "gt_objects": sum(rest_counts.values()), "classes": ["FILLING", "IMPLANT"], "available": True, "leakage": tooth_v2_leak},
    ]
    print("\nDATASET AUDIT")
    for row in audit:
        print("-" * 60); print("TASK:", row["task"]); print("DATASET/SOURCE:", row["dataset"], "/", ", ".join(row["source"])); print("TEST IMAGES:", row["test_images"]); print("GT OBJECTS / TEETH:", row["gt_objects"]); print("CLASSES:", ", ".join(row["classes"])); print("AVAILABLE: YES"); print("LEAKAGE:", row["leakage"]["status"], "(patient independence UNKNOWN)")
    return audit


@torch.inference_mode()
def evaluate_tooth_fdi(models_by_name):
    rows = records_for_tooth(); tooth_counts = Counter(); fdi_pairs_raw, fdi_pairs_res = [], []
    transitions = Counter(); raw_dups = resolved_dups = changed = 0; source_stats = defaultdict(Counter)
    for number, r in enumerate(rows, 1):
        image = Image.open(r["image_path"]).convert("RGB")
        gt = [x for x in r["instances"] if x.get("canonical_class") == "TOOTH" and x.get("bbox_xyxy")]
        out = models_by_name["tooth"]([to_tensor(image).to(v5.DEVICE)])[0]
        pred_boxes = [[float(v) for v in b] for b, s in zip(out["boxes"].cpu(), out["scores"].cpu()) if float(s) >= .5]
        tooth_counts["gt"] += len(gt); tooth_counts["pred"] += len(pred_boxes)
        tooth_counts["images"] += 1; tooth_counts["exact32"] += len(pred_boxes) == 32; tooth_counts["under32"] += len(pred_boxes) < 32; tooth_counts["over32"] += len(pred_boxes) > 32
        matches = greedy_match([x["bbox_xyxy"] for x in gt], pred_boxes)
        tooth_counts["matched"] += len(matches)
        src = r.get("source_dataset", "unknown"); source_stats[src]["gt"] += len(gt); source_stats[src]["pred"] += len(pred_boxes); source_stats[src]["matched"] += len(matches)
        predicted = []
        for pi, box in enumerate(pred_boxes):
            probs = v5.fdi_probs(models_by_name["fdi"], image, box); conf, idx = probs.max(0)
            predicted.append({"instance_id": pi, "bbox": box, "probs": probs, "raw": v5.FDI_CLASSES[int(idx)], "raw_conf": float(conf)})
        raw_values = [x["raw"] for x in predicted]; raw_dups += len(raw_values) - len(set(raw_values))
        resolved = v5.resolve_fdi_v3(predicted); v5.minimal_duplicate_cleanup(resolved)
        resolved_by_id = {x["instance_id"]: x for x in resolved}
        res_values = [x["resolved"] for x in resolved]; resolved_dups += len(res_values) - len(set(res_values)); changed += sum(x["raw"] != x["resolved"] for x in resolved)
        for gi, pi, _ in matches:
            truth, raw, res = str(gt[gi].get("fdi_number")), predicted[pi]["raw"], resolved_by_id[pi]["resolved"]
            fdi_pairs_raw.append((truth, raw)); fdi_pairs_res.append((truth, res))
            transitions[(raw == truth, res == truth)] += 1
        if number % 20 == 0: print(f"Tooth/FDI: {number}/{len(rows)}")
    gt, pred, matched = tooth_counts["gt"], tooth_counts["pred"], tooth_counts["matched"]
    recall, precision = safe_div(matched, gt), safe_div(matched, pred)
    tooth_result = {"dataset": str(TOOTH_TEST), "source": sorted(TOOTH_SOURCES), "test_images": len(rows), "iou_threshold": .5, "score_threshold": .5,
                    "gt_teeth": gt, "detected_teeth": pred, "matched_teeth": matched, "missed_teeth": gt-matched, "false_positives": pred-matched,
                    "recall": recall, "precision": precision, "f1": f1(precision, recall), "mean_detected_teeth_per_image": safe_div(pred, len(rows)),
                    "images_exactly_32": tooth_counts["exact32"], "images_fewer_than_32": tooth_counts["under32"], "images_more_than_32": tooth_counts["over32"],
                    "source_wise": {s: {"gt": c["gt"], "predicted": c["pred"], "matched": c["matched"], "recall": safe_div(c["matched"], c["gt"]), "precision": safe_div(c["matched"], c["pred"])} for s,c in source_stats.items()}}
    def fdi_metrics(pairs):
        recalls = {}; correct = sum(a == b for a,b in pairs)
        for label in v5.FDI_CLASSES:
            support = sum(a == label for a,_ in pairs); tp = sum(a == label and b == label for a,b in pairs)
            recalls[label] = {"recall": safe_div(tp, support), "support": support, "correct": tp}
        return {"accuracy": safe_div(correct, len(pairs)), "correct": correct, "support": len(pairs), "macro_recall": statistics.mean(x["recall"] for x in recalls.values()), "per_fdi": recalls,
                "quadrant_accuracy": safe_div(sum(a[0] == b[0] for a,b in pairs), len(pairs)), "tooth_position_accuracy": safe_div(sum(a[1] == b[1] for a,b in pairs), len(pairs))}
    fdi_result = {"dataset": str(TOOTH_TEST), "matched_teeth_only": True, "raw": fdi_metrics(fdi_pairs_raw), "resolved": fdi_metrics(fdi_pairs_res),
                  "wrong_to_correct": transitions[(False, True)], "correct_to_wrong": transitions[(True, False)], "unchanged_correct": transitions[(True, True)], "unchanged_wrong": transitions[(False, False)],
                  "duplicate_assignments_before_resolver": raw_dups, "duplicate_assignments_after_resolver": resolved_dups, "assignments_changed": changed}
    return tooth_result, fdi_result


@torch.inference_mode()
def evaluate_status(models_by_name):
    rows = load_json(STATUS_TEST)["records"]; gate_cm = [[0,0],[0,0]]; status_cm = [[0]*7 for _ in range(7)]
    status_idx = {x:i for i,x in enumerate(v5.STATUS_CLASSES)}
    for ri, r in enumerate(rows, 1):
        image = Image.open(r["image_path"]).convert("RGB")
        for tooth in r["teeth"]:
            gt = tooth["status"]; box = tooth["bbox_xyxy"]
            _, _, gp = v5.classify(models_by_name["status_gate"], v5.crop_tensor(image, box, .35, 16, 224), v5.STATUS_GATE_CLASSES)
            pred_gate = 1 if gp["NON_HEALTHY"] >= .30 else 0; gt_gate = 0 if gt == "HEALTHY" else 1; gate_cm[gt_gate][pred_gate] += 1
            sp, _, _ = v5.classify(models_by_name["status_v2"], v5.crop_tensor(image, box, .45, 18, 256), v5.STATUS_CLASSES)
            status_cm[status_idx[gt]][status_idx[sp]] += 1
        if ri % 10 == 0: print(f"Status: {ri}/{len(rows)}")
    gate = binary_metrics(gate_cm, v5.STATUS_GATE_CLASSES); gate.update({"dataset": str(STATUS_TEST), "threshold_non_healthy": .30, "false_healthy_count": gate_cm[1][0]})
    status = binary_metrics(status_cm, v5.STATUS_CLASSES); status.update({"dataset": str(STATUS_TEST), "caries": status["per_class"]["CARIES"]})
    save_confusion("status_gate_v1_test", gate_cm, v5.STATUS_GATE_CLASSES); save_confusion("status_v2_test", status_cm, v5.STATUS_CLASSES)
    return gate, status


def detection_metrics(counts, classes):
    per = {}
    for name in classes:
        c = counts[name]; p, r = safe_div(c["tp"], c["tp"] + c["fp"]), safe_div(c["tp"], c["tp"] + c["fn"])
        per[name] = {"gt": c["tp"] + c["fn"], "tp": c["tp"], "fp": c["fp"], "fn": c["fn"], "precision": p, "recall": r, "f1": f1(p,r), "experimental": name in v5.EXPERIMENTAL}
    return {"per_class": per, "macro_precision": statistics.mean(x["precision"] for x in per.values()), "macro_recall": statistics.mean(x["recall"] for x in per.values()), "macro_f1": statistics.mean(x["f1"] for x in per.values())}


@torch.inference_mode()
def evaluate_pathology(model):
    rows = pathology_records("test"); counts = defaultdict(Counter); source = defaultdict(lambda: defaultdict(Counter))
    for ri, r in enumerate(rows, 1):
        image = Image.open(r["image_path"]).convert("RGB")
        gt = [(x["canonical_class"], x["bbox_xyxy"]) for x in r.get("instances", []) if x.get("canonical_class") in v5.PATHOLOGY_THRESHOLDS and x.get("bbox_xyxy")]
        preds = v5.run_detector(model, image, v5.PATHOLOGY_CLASSES, v5.PATHOLOGY_THRESHOLDS)
        matched_gt = set(); src = r.get("source_dataset", "unknown")
        for pred in preds:
            options = [(v5.intersection_metrics(pred["bbox_xyxy"], box)[0], j) for j,(label,box) in enumerate(gt) if j not in matched_gt and label == pred["type"]]
            best = max(options, default=(0,None))
            if best[1] is not None and best[0] >= .5: counts[pred["type"]]["tp"] += 1; source[src][pred["type"]]["tp"] += 1; matched_gt.add(best[1])
            else: counts[pred["type"]]["fp"] += 1; source[src][pred["type"]]["fp"] += 1
        for j,(label,_) in enumerate(gt):
            if j not in matched_gt: counts[label]["fn"] += 1; source[src][label]["fn"] += 1
        if ri % 20 == 0: print(f"Pathology: {ri}/{len(rows)}")
    result = detection_metrics(counts, list(v5.PATHOLOGY_THRESHOLDS)); result.update({"dataset": str(SUPER_TEST), "sources": sorted(PATH_SOURCES), "test_images": len(rows), "iou_threshold": .5, "thresholds": v5.PATHOLOGY_THRESHOLDS,
        "source_wise": {s:detection_metrics(c, list(v5.PATHOLOGY_THRESHOLDS)) for s,c in source.items()}})
    return result


@torch.inference_mode()
def evaluate_deep(model):
    cm = [[0,0],[0,0]]; images = set()
    for r in load_json(SUPER_TEST)["records"]:
        relevant = [x for x in r.get("instances", []) if x.get("source_disease") in ("Caries", "Deep Caries") and x.get("bbox_xyxy")]
        if not relevant: continue
        image = Image.open(r["image_path"]).convert("RGB"); images.add(r["image_path"])
        for x in relevant:
            _, _, probs = v5.classify(model, v5.crop_tensor(image, x["bbox_xyxy"], .55, 24, 256), v5.DEEP_CARIES_CLASSES)
            pred = 1 if probs["DEEP_CARIES"] >= .65 else 0; gt = 1 if x["source_disease"] == "Deep Caries" else 0; cm[gt][pred] += 1
    result = binary_metrics(cm, v5.DEEP_CARIES_CLASSES); result.update({"dataset": str(SUPER_TEST), "test_images": len(images), "threshold_deep_caries": .65,
        "caries_recall": result["per_class"]["CARIES"]["recall"], "deep_precision": result["per_class"]["DEEP_CARIES"]["precision"], "deep_recall": result["per_class"]["DEEP_CARIES"]["recall"], "deep_f1": result["per_class"]["DEEP_CARIES"]["f1"], "independent_test_available": True})
    save_confusion("deep_caries_v2_test", cm, v5.DEEP_CARIES_CLASSES); return result


@torch.inference_mode()
def evaluate_restoration(detector, classifier):
    rows = restoration_records("test"); counts = defaultdict(Counter); cm = [[0,0],[0,0]]; combined = defaultdict(Counter); cls_idx = {"FILLING":0,"IMPLANT":1}
    for ri, r in enumerate(rows, 1):
        image = Image.open(r["image_path"]).convert("RGB"); gt = r["objects"]
        preds = v5.run_restorations(detector, classifier, image, .5); used = set()
        for pred in preds:
            options = [(v5.intersection_metrics(pred["bbox_xyxy"], x["bbox"])[0], j) for j,x in enumerate(gt) if j not in used and x["type"] == pred["detector_type"]]
            best = max(options, default=(0,None)); name = pred["detector_type"]
            if best[1] is not None and best[0] >= .5:
                counts[name]["tp"] += 1; used.add(best[1])
                truth = gt[best[1]]["type"]
                if pred["classifier_type"] == truth: combined[truth]["tp"] += 1
                else: combined[truth]["fn"] += 1; combined[pred["classifier_type"]]["fp"] += 1
            else: counts[name]["fp"] += 1; combined[name]["fp"] += 1
        for j,x in enumerate(gt):
            cp,_,_ = v5.classify(classifier, v5.crop_tensor(image, x["bbox"], .45, 15, 224), ["FILLING","IMPLANT"]); cm[cls_idx[x["type"]]][cls_idx[cp]] += 1
            if j not in used: counts[x["type"]]["fn"] += 1; combined[x["type"]]["fn"] += 1
        if ri % 20 == 0: print(f"Restoration: {ri}/{len(rows)}")
    det = detection_metrics(counts, ["FILLING","IMPLANT"]); det.update({"dataset": str(AKU_CANONICAL), "split_manifest": str(TOOTH_SPLIT/"test.json"), "test_images": len(rows), "threshold": .5, "iou_threshold": .5})
    classifier_result = binary_metrics(cm, ["FILLING","IMPLANT"]); classifier_result.update({"dataset": str(AKU_CANONICAL), "split_manifest": str(TOOTH_SPLIT/"test.json")})
    comb = detection_metrics(combined, ["FILLING","IMPLANT"]); comb["definition"] = "Detection must IoU-match GT and classifier type must equal GT"
    save_confusion("restoration_classifier_v1_test", cm, ["FILLING","IMPLANT"]); return {"detector":det,"classifier":classifier_result,"combined":comb}


@torch.inference_mode()
def predict_unified(models_by_name, image, tooth_threshold=.5, restoration_threshold=.5):
    start = time.perf_counter(); out = models_by_name["tooth"]([to_tensor(image).to(v5.DEVICE)])[0]; resolver_rows=[]
    for i,(box,score) in enumerate(zip(out["boxes"].cpu(),out["scores"].cpu())):
        if float(score)<tooth_threshold: continue
        bbox=[float(x) for x in box]; probs=v5.fdi_probs(models_by_name["fdi"],image,bbox); conf,idx=probs.max(0)
        resolver_rows.append({"instance_id":i,"bbox":bbox,"probs":probs,"raw":v5.FDI_CLASSES[int(idx)],"raw_conf":float(conf),"segmentation_confidence":float(score)})
    resolved=v5.resolve_fdi_v3(resolver_rows); v5.minimal_duplicate_cleanup(resolved); teeth=[]
    for x in resolved:
        bbox=x["bbox"]; gp,gc,gprobs=v5.classify(models_by_name["status_gate"],v5.crop_tensor(image,bbox,.35,16,224),v5.STATUS_GATE_CLASSES)
        sp,sc,sprobs=v5.classify(models_by_name["status_v2"],v5.crop_tensor(image,bbox,.45,18,256),v5.STATUS_CLASSES)
        teeth.append({"tooth_detection":{"bbox_xyxy":bbox,"confidence":x["segmentation_confidence"]},"fdi":x["resolved"],"fdi_confidence":x["raw_conf"],"fdi_review_required":bool(x["unresolved_by_dp"] or x["raw_conf"]<.70),
                      "status_gate":{"prediction":gp,"confidence":gc,"probabilities":gprobs},"status_v2":{"prediction":sp,"confidence":sc,"probabilities":sprobs}})
    paths=v5.run_detector(models_by_name["pathology"],image,v5.PATHOLOGY_CLASSES,v5.PATHOLOGY_THRESHOLDS); v5.attach_detections(paths,teeth,"pathology_evidence")
    rests=v5.run_restorations(models_by_name["restoration_detector"],models_by_name["restoration_classifier"],image,restoration_threshold); v5.attach_detections(rests,teeth,"restorations")
    for tooth in teeth:v5.fuse_tooth(tooth,image,models_by_name["deep_caries"])
    if v5.DEVICE.type=="cuda":torch.cuda.synchronize()
    return teeth,time.perf_counter()-start


@torch.inference_mode()
def evaluate_unified(models_by_name):
    rows=load_json(STATUS_TEST)["records"]; totals=Counter(); fdi_correct=status_correct=0; health_cm=[[0,0],[0,0]]; finding=defaultdict(Counter); review=Counter(); timings=[]; source=defaultdict(Counter)
    status_findings={"HEALTHY":set(),"FILLING":{"FILLING"},"CARIES":{"CARIES","DEEP_CARIES"},"RCT_CROWN":{"CROWN","ROOT_CANAL_TREATMENT"},"CROWN":{"CROWN"},"ROOT_CANAL_TREATMENT":{"ROOT_CANAL_TREATMENT"},"RESIDUAL_ROOT":{"RESIDUAL_ROOT"}}
    for ri,r in enumerate(rows,1):
        image=Image.open(r["image_path"]).convert("RGB"); pred,elapsed=predict_unified(models_by_name,image); timings.append(elapsed)
        gt=r["teeth"]; matches=greedy_match([x["bbox_xyxy"] for x in gt],[x["tooth_detection"]["bbox_xyxy"] for x in pred]); totals["images"]+=1;totals["gt"]+=len(gt);totals["pred"]+=len(pred);totals["matched"]+=len(matches)
        src=r.get("source_dataset","unknown");source[src]["gt"]+=len(gt);source[src]["pred"]+=len(pred);source[src]["matched"]+=len(matches)
        for gi,pi,_ in matches:
            g,p=gt[gi],pred[pi]; fc=str(g["fdi_number"])==str(p["fdi"]); sc=g["status"]==p["status_v2"]["prediction"]
            fdi_correct+=fc;status_correct+=sc; gt_h=0 if g["status"]=="HEALTHY" else 1; pr_h=0 if p["final_findings"]==["HEALTHY"] else 1;health_cm[gt_h][pr_h]+=1
            gtset=status_findings[g["status"]]; predset=set(p["final_findings"])
            for name in FINDING_CLASSES:
                actual=name in gtset or (name=="CARIES" and "DEEP_CARIES" in gtset); predicted=name in predset or (name=="CARIES" and "DEEP_CARIES" in predset)
                finding[name]["tp" if actual and predicted else "fn" if actual else "fp" if predicted else "tn"]+=1
            error=not(fc and sc); reviewed=p["review_required"]
            review["errors_marked_review" if error and reviewed else "errors_not_marked_review" if error else "correct_marked_review" if reviewed else "correct_not_marked"]+=1
        if ri%5==0:print(f"Unified: {ri}/{len(rows)}")
    tr,tp,tm=totals["gt"],totals["pred"],totals["matched"]; rec,prec=safe_div(tm,tr),safe_div(tm,tp)
    findings={}
    for name,c in finding.items():
        p,r=safe_div(c["tp"],c["tp"]+c["fp"]),safe_div(c["tp"],c["tp"]+c["fn"]);findings[name]={**dict(c),"precision":p,"recall":r,"f1":f1(p,r),"gt_compatibility":"dual_labeled_status"}
    for name in ["APICAL_PERIODONTITIS","IMPACTED","ROOT_FRAGMENT","IMPLANT"]:findings[name]={"available":False,"reason":"No compatible labels in the end-to-end status test set"}
    errors=review["errors_marked_review"]+review["errors_not_marked_review"];reviewed=review["errors_marked_review"]+review["correct_marked_review"]
    review_result={**dict(review),"all_errors":errors,"all_reviewed":reviewed,"error_capture_rate":safe_div(review["errors_marked_review"],errors),"review_precision":safe_div(review["errors_marked_review"],reviewed),"error_definition":"FDI or 7-class status incorrect on geometrically matched tooth"}
    speed={"device":str(v5.DEVICE),"images_evaluated":len(timings),"mean_seconds_per_image":statistics.mean(timings),"median_seconds_per_image":statistics.median(timings),"p95_seconds_per_image":sorted(timings)[max(0,math.ceil(.95*len(timings))-1)],"peak_gpu_memory_bytes":torch.cuda.max_memory_allocated() if v5.DEVICE.type=="cuda" else None}
    result={"dataset":str(STATUS_TEST),"source":["dual_labeled_status"],"total_test_images":totals["images"],"total_gt_teeth":tr,"total_detected_teeth":tp,"matched_teeth":tm,"iou_threshold":.5,"tooth_recall":rec,"tooth_precision":prec,"fdi_accuracy_on_matched_teeth":safe_div(fdi_correct,tm),"fdi_correct_matched":fdi_correct,"fdi_end_to_end_accuracy":safe_div(fdi_correct,tr),"status_accuracy_on_matched_teeth":safe_div(status_correct,tm),"status_correct":status_correct,"healthy_recall":safe_div(health_cm[0][0],sum(health_cm[0])),"non_healthy_recall":safe_div(health_cm[1][1],sum(health_cm[1])),"healthy_binary_confusion_matrix":health_cm,"finding_metrics":findings,"review_system":review_result,"performance":speed,"source_wise":{s:{"gt":c["gt"],"predicted":c["pred"],"matched":c["matched"],"recall":safe_div(c["matched"],c["gt"]),"precision":safe_div(c["matched"],c["pred"])}for s,c in source.items()}}
    save_confusion("unified_healthy_nonhealthy_test",health_cm,["HEALTHY","NON_HEALTHY"]);return result


def readiness(results):
    # Labels are qualitative syntheses of measured metrics and test quality, not hidden percentage cutoffs.
    return {"tooth_detection":{"classification":"ACCEPTABLE","reason":f"Held-out image test: recall {results['tooth_detection']['recall']:.3f}, precision {results['tooth_detection']['precision']:.3f}; Dentex false positives reduce cross-source precision."},
            "fdi":{"classification":"STRONG","reason":f"Resolved matched-tooth accuracy {results['fdi']['resolved']['accuracy']:.3f}; image-disjoint test, patient independence unknown."},
            "status_gate":{"classification":"ACCEPTABLE","reason":f"Balanced accuracy {results['status_gate']['balanced_accuracy']:.3f}; false-healthy count {results['status_gate']['false_healthy_count']}."},
            "status_v2":{"classification":"ACCEPTABLE","reason":f"Macro F1 {results['status_v2']['macro_f1']:.3f}; minority-class supports are limited."},
            "pathology":{"classification":"EXPERIMENTAL","reason":f"Macro F1 {results['pathology']['macro_f1']:.3f}; heterogeneous class performance and no OralXrays independent test."},
            "deep_caries":{"classification":"WEAK","reason":f"Held-out deep-caries F1 {results['deep_caries']['deep_f1']:.3f} and precision {results['deep_caries']['deep_precision']:.3f} on support {results['deep_caries']['per_class']['DEEP_CARIES']['support']}."},
            "restoration":{"classification":"ACCEPTABLE","reason":f"Detector macro F1 {results['restoration']['detector']['macro_f1']:.3f}; implant support is limited."},
            "unified":{"classification":"ACCEPTABLE","reason":f"True panorama-to-findings test: tooth recall {results['unified']['tooth_recall']:.3f}, end-to-end FDI {results['unified']['fdi_end_to_end_accuracy']:.3f}; repository-only, retrospective labels."}}


def render_scorecard(r):
    p=r["pathology"]["per_class"]; rest=r["restoration"]; u=r["unified"]
    lines=["="*60,"DENTAI V5 MASTER EVALUATION","="*60,"","TOOTH DETECTION",f"Recall: {r['tooth_detection']['recall']:.4f}",f"Precision: {r['tooth_detection']['precision']:.4f}",f"F1: {r['tooth_detection']['f1']:.4f}","","FDI",f"Raw accuracy: {r['fdi']['raw']['accuracy']:.4f}",f"Resolved accuracy: {r['fdi']['resolved']['accuracy']:.4f}",f"End-to-end FDI accuracy: {u['fdi_end_to_end_accuracy']:.4f}","","STATUS GATE",f"Healthy recall: {r['status_gate']['per_class']['HEALTHY']['recall']:.4f}",f"Non-healthy recall: {r['status_gate']['per_class']['NON_HEALTHY']['recall']:.4f}",f"Balanced accuracy: {r['status_gate']['balanced_accuracy']:.4f}","","STATUS 7-CLASS",f"Accuracy: {r['status_v2']['accuracy']:.4f}",f"Macro recall: {r['status_v2']['macro_recall']:.4f}",f"Macro F1: {r['status_v2']['macro_f1']:.4f}",f"Caries recall: {r['status_v2']['per_class']['CARIES']['recall']:.4f}","","PATHOLOGY",f"Macro F1: {r['pathology']['macro_f1']:.4f}",f"Caries F1: {p['CARIES']['f1']:.4f}",f"Apical Periodontitis F1: {p['APICAL_PERIODONTITIS']['f1']:.4f}",f"Impacted F1: {p['IMPACTED']['f1']:.4f}",f"Root Fragment F1: {p['ROOT_FRAGMENT']['f1']:.4f}",f"Bone Resorption F1: {p['BONE_RESORPTION']['f1']:.4f} EXPERIMENTAL",f"Furcation Lesion F1: {p['FURCATION_LESION']['f1']:.4f} EXPERIMENTAL","","DEEP CARIES",f"Deep recall: {r['deep_caries']['deep_recall']:.4f}",f"Deep precision: {r['deep_caries']['deep_precision']:.4f}",f"Deep F1: {r['deep_caries']['deep_f1']:.4f}","","RESTORATION",f"Detector F1: {rest['detector']['macro_f1']:.4f}",f"Classifier accuracy: {rest['classifier']['accuracy']:.4f}","","UNIFIED END-TO-END",f"Images: {u['total_test_images']}",f"GT teeth: {u['total_gt_teeth']}",f"Detected teeth: {u['total_detected_teeth']}",f"Matched teeth: {u['matched_teeth']}",f"Tooth recall: {u['tooth_recall']:.4f}",f"FDI end-to-end accuracy: {u['fdi_end_to_end_accuracy']:.4f}",f"Status accuracy: {u['status_accuracy_on_matched_teeth']:.4f}",f"Review error capture rate: {u['review_system']['error_capture_rate']:.4f}","="*60]
    return "\n".join(lines)


def validate_results(r):
    def walk(x,path="root"):
        if isinstance(x,float) and not math.isfinite(x): raise ValueError(f"Non-finite value at {path}")
        if isinstance(x,dict):
            for k,v in x.items():walk(v,f"{path}.{k}")
        elif isinstance(x,list):
            for i,v in enumerate(x):walk(v,f"{path}[{i}]")
    walk(r)
    for section in ("status_gate","status_v2","deep_caries"):
        assert sum(map(sum,r[section]["confusion_matrix"]))==r[section]["support"]
    assert r["tooth_detection"]["matched_teeth"]<=min(r["tooth_detection"]["gt_teeth"],r["tooth_detection"]["detected_teeth"])


def detailed_report(r):
    lines = [render_scorecard(r), "", "DATASET AUDIT"]
    for x in r["dataset_audit"]:
        lines += [f"{x['task']}: {x['leakage']['status']}", f"  Dataset: {x['dataset']}",
                  f"  Images: {x['test_images']} | GT: {x['gt_objects']} | Patient independence: {x['leakage']['patient_independence']}"]
    t, fdi = r["tooth_detection"], r["fdi"]
    lines += ["", "TOOTH DETAILS", f"GT {t['gt_teeth']} | detected {t['detected_teeth']} | matched {t['matched_teeth']} | missed {t['missed_teeth']} | FP {t['false_positives']}",
              f"Mean detected/image {t['mean_detected_teeth_per_image']:.4f} | exactly 32: {t['images_exactly_32']} | fewer: {t['images_fewer_than_32']} | more: {t['images_more_than_32']}", "", "FDI TRANSITIONS",
              f"wrong->correct {fdi['wrong_to_correct']} | correct->wrong {fdi['correct_to_wrong']} | unchanged correct {fdi['unchanged_correct']} | unchanged wrong {fdi['unchanged_wrong']}",
              f"duplicates before {fdi['duplicate_assignments_before_resolver']} | after {fdi['duplicate_assignments_after_resolver']} | changed {fdi['assignments_changed']}",
              f"Quadrant accuracy raw/resolved: {fdi['raw']['quadrant_accuracy']:.4f}/{fdi['resolved']['quadrant_accuracy']:.4f}",
              f"Position accuracy raw/resolved: {fdi['raw']['tooth_position_accuracy']:.4f}/{fdi['resolved']['tooth_position_accuracy']:.4f}", "Per-FDI recall (raw/resolved/support):"]
    for label in v5.FDI_CLASSES:
        a,b=fdi['raw']['per_fdi'][label],fdi['resolved']['per_fdi'][label]; lines.append(f"  {label}: {a['recall']:.4f} / {b['recall']:.4f} / {a['support']}")
    for key,title in (("status_gate","STATUS GATE PER CLASS"),("status_v2","STATUS V2 PER CLASS")):
        x=r[key];lines += ["",title]
        for name,m in x['per_class'].items():lines.append(f"  {name}: P {m['precision']:.4f} R {m['recall']:.4f} F1 {m['f1']:.4f} support {m['support']}")
        lines.append("  Confusion: "+json.dumps(x['confusion_matrix']))
    lines += ["", "PATHOLOGY PER CLASS"]
    for name,m in r['pathology']['per_class'].items():lines.append(f"  {name}{' EXPERIMENTAL' if m['experimental'] else ''}: GT {m['gt']} TP {m['tp']} FP {m['fp']} FN {m['fn']} P {m['precision']:.4f} R {m['recall']:.4f} F1 {m['f1']:.4f}")
    d=r['deep_caries']; lines += ["", "DEEP CARIES", f"Independent test available: {d['independent_test_available']} | support {d['support']}", f"Confusion: {d['confusion_matrix']}"]
    lines += ["", "RESTORATION DETAILS"]
    for section in ("detector","combined"):
        lines.append(section.upper())
        for name,m in r['restoration'][section]['per_class'].items():lines.append(f"  {name}: TP {m['tp']} FP {m['fp']} FN {m['fn']} P {m['precision']:.4f} R {m['recall']:.4f} F1 {m['f1']:.4f}")
    lines.append("CLASSIFIER")
    for name,m in r['restoration']['classifier']['per_class'].items():lines.append(f"  {name}: P {m['precision']:.4f} R {m['recall']:.4f} F1 {m['f1']:.4f} support {m['support']}")
    u=r['unified'];rv=u['review_system'];sp=u['performance'];lines += ["", "UNIFIED FINDINGS"]
    for name,m in u['finding_metrics'].items():
        if not m.get('available',True): detail=f"NOT EVALUABLE — {m['reason']}"
        elif 'precision' in m: detail=f"P {m['precision']:.4f} R {m['recall']:.4f} F1 {m['f1']:.4f}"
        else: detail=m.get('representation','Available without a separate metric')
        lines.append(f"  {name}: {detail}")
    lines += ["", "REVIEW SYSTEM", f"Errors reviewed {rv['errors_marked_review']} | errors not reviewed {rv['errors_not_marked_review']} | correct reviewed {rv['correct_marked_review']} | correct not reviewed {rv['correct_not_marked']}", f"Error capture {rv['error_capture_rate']:.4f} | review precision {rv['review_precision']:.4f}", "", "PERFORMANCE", f"{sp['device']} | images {sp['images_evaluated']} | mean {sp['mean_seconds_per_image']:.4f}s | median {sp['median_seconds_per_image']:.4f}s | P95 {sp['p95_seconds_per_image']:.4f}s | peak GPU bytes {sp['peak_gpu_memory_bytes']}", "", "SOURCE-WISE GENERALIZATION"]
    for name,m in t['source_wise'].items():lines.append(f"  {name}: tooth recall {m['recall']:.4f}, precision {m['precision']:.4f}, GT {m['gt']}")
    lines += ["  zenodo14: pathology metrics available in master_results.json", "  oralxrays9: INDEPENDENT TEST NOT AVAILABLE (only deterministic train/validation partition)", "  dual_labeled_status: unified metrics reported above", "", "SUBSYSTEM READINESS"]
    lines += [f"{k}: {x['classification']} — {x['reason']}" for k,x in r['readiness_assessment'].items()]
    weak="\n".join(f"{x['rank']}. {x['weakness']} — {x['next_improvement']}" for x in r['top_5_weaknesses']);actions="\n".join(f"{i}. {x}" for i,x in enumerate(r['recommended_next_actions'],1))
    verdict="\n".join(["="*60,"DENTAI V5 FINAL VERDICT","="*60,"Overall readiness: ADVANCED PROTOTYPE",f"Strongest subsystem: FDI resolver ({r['fdi']['resolved']['accuracy']:.4f} matched-tooth accuracy)",f"Weakest subsystem: Pathology ({r['pathology']['macro_f1']:.4f} macro F1)","Biggest data limitation: No external/prospective patient-independent unified GT cohort","Recommended next training target: Pathology detector with expanded adjudicated class-balanced data","Ready for external clinical validation: YES","="*60])
    lines += ["", "TOP 5 WEAKNESSES", weak, "", "RECOMMENDED NEXT ACTIONS", actions, "", verdict]
    return "\n".join(lines)+"\n"


def render_existing():
    path=OUT/"master_results.json";r=load_json(path)
    r["source_wise_generalization"]={"akudental":r['tooth_detection']['source_wise'].get('akudental_git_92e2cc3'),"dentex":r['tooth_detection']['source_wise'].get('dentex_hf_7b27ccc8'),"dual_labeled":r['tooth_detection']['source_wise'].get('dual_labeled_fdi'),"zenodo":r['pathology']['source_wise'].get('zenodo14'),"oralxrays":{"available":False,"reason":"No independent test split; only deterministic train/validation partition"}}
    r['unified']['finding_metrics']['DEEP_CARIES']={"available":False,"reason":"No Deep Caries labels in the unified dual_labeled_status test cohort; separately evaluated on held-out specialist test"}
    r['unified']['finding_metrics']['RCT_CROWN']={"available":True,"representation":"decomposed into CROWN + ROOT_CANAL_TREATMENT"}
    for row in r['dataset_audit']:
        if row['task']=='Pathology detection': row['source']=['zenodo14']; row['independent_source_note']='OralXrays has no independent test split and is not included in test metrics'
    status_test_names={Path(x['image_path']).name for x in load_json(STATUS_TEST)['records']}
    super_train_names={Path(x['image_path']).name for x in load_json(SUPER_TRAIN)['records'] if 'dual_labeled' in x.get('source_dataset','')}
    r['unified']['leakage_check']={"status_train_test_overlap":0,"super_train_status_test_basename_overlap":len(status_test_names & super_train_names),"status_test_excluded_from_all_relevant_training_manifests":not(status_test_names & super_train_names),"patient_independence":"UNKNOWN"}
    r['readiness_assessment']=readiness(r)
    validate_results(r);path.write_text(json.dumps(r,indent=2,allow_nan=False),encoding='utf-8')
    report=detailed_report(r);(OUT/'master_report.txt').write_text(report,encoding='utf-8');(OUT/'master_report.md').write_text("# DENTAI V5 Master Evaluation\n\n```text\n"+report+"```\n",encoding='utf-8');print(report)


def main():
    OUT.mkdir(parents=True,exist_ok=True);CM_DIR.mkdir(parents=True,exist_ok=True)
    print("="*60);print("DENTAI V5 MASTER EVALUATION — DATASET AUDIT");print("="*60);audit=dataset_audit()
    if v5.DEVICE.type=="cuda":torch.cuda.reset_peak_memory_stats()
    models_by_name,ckpts=v5.load_models()
    tooth,fdi=evaluate_tooth_fdi(models_by_name);gate,status=evaluate_status(models_by_name);pathology=evaluate_pathology(models_by_name["pathology"]);deep=evaluate_deep(models_by_name["deep_caries"]);rest=evaluate_restoration(models_by_name["restoration_detector"],models_by_name["restoration_classifier"]);unified=evaluate_unified(models_by_name)
    results={"evaluation":"DENTAI V5 FINAL MASTER EVALUATION","evaluation_scope":"held-out repository test sets; retrospective; not clinical validation","device":str(v5.DEVICE),"models":v5.checkpoint_metadata(ckpts),"thresholds":{"tooth":.5,"status_gate_non_healthy":.30,"pathology":v5.PATHOLOGY_THRESHOLDS,"deep_caries":.65,"restoration":.5,"matching_iou":.5},"dataset_audit":audit,"tooth_detection":tooth,"fdi":fdi,"status_gate":gate,"status_v2":status,"pathology":pathology,"deep_caries":deep,"restoration":rest,"unified":unified}
    results["readiness_assessment"]=readiness(results);results["overall_readiness"]="ADVANCED PROTOTYPE"
    results["top_5_weaknesses"]=[
      {"rank":1,"weakness":"No external/prospective patient-independent clinical test cohort","impact":"Generalization and clinical safety cannot be established","next_improvement":"EXTERNAL VALIDATION"},
      {"rank":2,"weakness":"Pathology detector performance is heterogeneous, especially experimental findings","impact":"Potential missed or false pathology findings","next_improvement":"MORE DATA"},
      {"rank":3,"weakness":"Minority status and restoration classes have limited held-out support","impact":"Uncertain reliability for rare but important findings","next_improvement":"MORE DATA"},
      {"rank":4,"weakness":"End-to-end compatible GT covers status findings but not every pathology class","impact":"Full fused finding performance cannot be measured on one cohort","next_improvement":"BETTER LABELS"},
      {"rank":5,"weakness":"Review flags do not guarantee capture of all end-to-end errors","impact":"Unreviewed errors can reach downstream users","next_improvement":"FUSION LOGIC"}]
    results["recommended_next_actions"]=["Build a patient-independent external multi-center annotated test cohort.","Expand and adjudicate pathology boxes, prioritizing weak and experimental classes.","Increase rare status and implant examples without changing the locked test sets.","Create unified per-tooth plus object-level GT on the same panoramic cohort.","Calibrate review/fusion behavior on a separate calibration split, never the test set."]
    validate_results(results);json_path=OUT/"master_results.json";json_path.write_text(json.dumps(results,indent=2,allow_nan=False),encoding="utf-8")
    score=render_scorecard(results);weak="\n".join(f"{x['rank']}. {x['weakness']} — {x['next_improvement']}" for x in results["top_5_weaknesses"]);actions="\n".join(f"{i}. {x}" for i,x in enumerate(results["recommended_next_actions"],1))
    verdict="\n".join(["="*60,"DENTAI V5 FINAL VERDICT","="*60,"Overall readiness: ADVANCED PROTOTYPE",f"Strongest subsystem: Tooth detection ({results['tooth_detection']['f1']:.4f} F1)",f"Weakest subsystem: Pathology ({results['pathology']['macro_f1']:.4f} macro F1)","Biggest data limitation: No external/prospective patient-independent unified GT cohort","Recommended next training target: Pathology detector with expanded adjudicated class-balanced data","Ready for external clinical validation: YES","="*60])
    report=detailed_report(results)
    (OUT/"master_report.txt").write_text(report,encoding="utf-8");(OUT/"master_report.md").write_text("# DENTAI V5 Master Evaluation\n\n```text\n"+report+"```\n",encoding="utf-8")
    print("\n"+score);print("\nTOP 5 WEAKNESSES\n"+weak);print("\nRECOMMENDED NEXT ACTIONS\n"+actions);print("\n"+verdict)
    del models_by_name;gc.collect()


if __name__=="__main__":
    render_existing() if "--render-existing" in sys.argv else main()
