"""Offline dataset and metric tests; none contact Gemini."""
import json
from pathlib import Path

from evaluate import DEFAULT_DATASET, DEFAULT_PREDICTIONS, score

ROOT = Path(__file__).parent
VALID = {"supported", "contradicted", "insufficient_evidence"}


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def aggregate(statuses):
    if "contradicted" in statuses:
        return "contradicted"
    if "insufficient_evidence" in statuses:
        return "insufficient_evidence"
    return "supported"


def test_dataset_cases_have_labels_and_reproducible_local_images():
    cases = load_jsonl(DEFAULT_DATASET)
    assert len(cases) == 9
    assert {claim["status"] for case in cases for claim in case["expected_claims"]} == VALID
    for case in cases:
        assert (ROOT / case["image"]).is_file()
        statuses = [claim["status"] for claim in case["expected_claims"]]
        assert case["expected_overall_status"] == aggregate(statuses)


def test_mixed_case_contains_all_verdicts_and_uses_contradiction_precedence():
    cases = load_jsonl(DEFAULT_DATASET)
    mixed = next(case for case in cases if case["case_id"] == "red-circle-mixed")
    statuses = [claim["status"] for claim in mixed["expected_claims"]]
    assert set(statuses) == VALID
    assert mixed["expected_overall_status"] == "contradicted"


def test_metrics_use_only_historical_successful_live_claims():
    report = score(DEFAULT_DATASET, DEFAULT_PREDICTIONS)
    assert report["evaluation_kind"] == "historical_live_smoke_outputs_only"
    assert report["matched_observed_claims"] == 2
    assert report["successful_observed_cases"] == 2
    assert report["failed_observed_cases"] == 1
    assert report["confusion_matrix_rows_expected_columns_predicted"] == [
        [1, 0, 0],
        [0, 1, 0],
        [0, 0, 0],
    ]
    assert report["per_class"]["supported"]["f1"] == 1.0
    assert report["per_class"]["contradicted"]["f1"] == 1.0
    assert report["per_class"]["insufficient_evidence"]["f1"] is None
