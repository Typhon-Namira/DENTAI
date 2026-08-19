import json
from pathlib import Path

from app.radar.engine import classify_signal


def test_multilingual_radar_benchmark_meets_baseline():
    rows = json.loads(Path("tests/fixtures/radar_semantic_eval.json").read_text(encoding="utf-8"))
    correct_candidate = 0
    correct_intent = 0
    checked_intent = 0
    for row in rows:
        result = classify_signal(row["text"], context_text=row.get("context") or None)
        correct_candidate += int(result.candidate is row["candidate"])
        if row.get("intent"):
            checked_intent += 1
            correct_intent += int(result.intent == row["intent"])
        if row.get("treatment"):
            assert result.treatment == row["treatment"], row["id"]
        if row.get("language"):
            assert result.language == row["language"], row["id"]
    assert correct_candidate / len(rows) >= 0.90
    assert correct_intent / checked_intent >= 0.85
