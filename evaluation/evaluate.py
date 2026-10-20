"""Score claim-level prediction JSONL against the labelled JSONL dataset.

This program makes no API calls. Only explicitly supplied observed outputs are
scored; dataset fixture responses are never treated as predictions.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sklearn.metrics import confusion_matrix, precision_recall_fscore_support

LABELS = ["supported", "contradicted", "insufficient_evidence"]
ROOT = Path(__file__).resolve().parent
DEFAULT_DATASET = ROOT / "data" / "cases.jsonl"
DEFAULT_PREDICTIONS = ROOT / "data" / "historical-live-smoke.jsonl"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def score(dataset_path: Path, predictions_path: Path) -> dict[str, Any]:
    cases = read_jsonl(dataset_path)
    predictions = read_jsonl(predictions_path)
    expected_by_key: dict[tuple[str, str], str] = {}
    known_case_ids: set[str] = set()
    for case in cases:
        if case["case_id"] in known_case_ids:
            raise ValueError(f"Duplicate case id: {case['case_id']}")
        known_case_ids.add(case["case_id"])
        for claim in case["expected_claims"]:
            status = claim["status"]
            if status not in LABELS:
                raise ValueError(f"Unknown expected status in case {case['case_id']}")
            key = (case["case_id"], claim["text"])
            if key in expected_by_key:
                raise ValueError(f"Duplicate expected claim: {key}")
            expected_by_key[key] = status

    y_true: list[str] = []
    y_pred: list[str] = []
    observed_case_ids: set[str] = set()
    failed_case_ids: set[str] = set()
    unmatched_predictions: list[dict[str, str]] = []
    seen_prediction_keys: set[tuple[str, str]] = set()
    for record in predictions:
        case_id = record["case_id"]
        if case_id not in known_case_ids:
            raise ValueError(f"Prediction references unknown case id: {case_id}")
        if record.get("http_status") != 200:
            failed_case_ids.add(case_id)
            continue
        observed_case_ids.add(case_id)
        for claim in record.get("observed_claims", []):
            status = claim.get("status")
            if status not in LABELS:
                raise ValueError(f"Unknown predicted status in case {case_id}")
            key = (case_id, claim.get("text", ""))
            if key in seen_prediction_keys:
                raise ValueError(f"Duplicate predicted claim: {key}")
            seen_prediction_keys.add(key)
            expected = expected_by_key.get(key)
            if expected is None:
                unmatched_predictions.append({"case_id": case_id, "text": key[1]})
                continue
            y_true.append(expected)
            y_pred.append(status)

    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=LABELS, zero_division=0
    )
    matrix = confusion_matrix(y_true, y_pred, labels=LABELS)
    per_class: dict[str, dict[str, float | int | None]] = {}
    for i, label in enumerate(LABELS):
        predicted_count = int(matrix[:, i].sum())
        # A class absent from both gold and model outputs is unmeasured, not 0%.
        unmeasured = int(support[i]) == 0 and predicted_count == 0
        per_class[label] = {
            "precision": None if unmeasured else float(precision[i]),
            "recall": None if unmeasured else float(recall[i]),
            "f1": None if unmeasured else float(f1[i]),
            "support": int(support[i]),
            "predicted_count": predicted_count,
        }

    return {
        "evaluation_kind": "historical_live_smoke_outputs_only",
        "dataset_cases": len(cases),
        "dataset_labelled_claims": len(expected_by_key),
        "successful_observed_cases": len(observed_case_ids),
        "failed_observed_cases": len(failed_case_ids),
        "matched_observed_claims": len(y_true),
        "unmatched_prediction_claims": unmatched_predictions,
        "expected_claims_without_observed_prediction": len(expected_by_key) - len(y_true),
        "dataset_cases_without_successful_observation": len(known_case_ids - observed_case_ids),
        "labels_in_order": LABELS,
        "confusion_matrix_rows_expected_columns_predicted": matrix.tolist(),
        "per_class": per_class,
        "interpretation": (
            "Exploratory smoke-check metrics only; two historical live claims, one per observed class. "
            "Not a representative benchmark, general accuracy estimate, or result from fixture responses."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--output", type=Path, help="Optional path to save the JSON report")
    args = parser.parse_args()
    report = score(args.dataset, args.predictions)
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
