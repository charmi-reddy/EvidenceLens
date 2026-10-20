"""Offline fixture tests: these validate schema and aggregation without Gemini."""
import json
from pathlib import Path

import pytest

from gemini_service import _check_overall_status
from schemas import AnalysisResult

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("fixture_name", "expected_status"),
    [
        ("evidencelens-supported.json", "supported"),
        ("evidencelens-contradicted.json", "contradicted"),
        ("evidencelens-insufficient.json", "insufficient_evidence"),
    ],
)
def test_single_verdict_fixtures_validate(fixture_name: str, expected_status: str):
    result = AnalysisResult.model_validate(load_fixture(fixture_name))
    _check_overall_status(result)
    assert result.overall_status.value == expected_status
    assert len(result.claims) == 1
    assert result.claims[0].status.value == expected_status
    assert result.claims[0].evidence
    assert result.claims[0].explanation


def test_mixed_fixture_validates_claims_and_aggregates_overall_status():
    result = AnalysisResult.model_validate(load_fixture("evidencelens-mixed-claims.json"))
    _check_overall_status(result)
    statuses = [claim.status.value for claim in result.claims]
    assert statuses == ["supported", "contradicted", "insufficient_evidence"]
    assert result.overall_status.value == "contradicted"
    assert len(result.limitations) == 2


@pytest.mark.parametrize(
    "raw_model_text",
    [
        "not-json",
        json.dumps({
            "overall_status": "supported",
            "claims": [{"text": "A claim", "status": "supported", "evidence": "visible",
                        "explanation": "matches", "confidence": "certain"}],
            "limitations": [],
        }),
        json.dumps({
            "overall_status": "supported",
            "claims": [{"text": "A claim", "status": "contradicted", "evidence": "visible",
                        "explanation": "conflicts", "confidence": "high"}],
            "limitations": [],
        }),
    ],
    ids=["invalid-json", "invalid-schema", "inconsistent-overall"],
)
def test_malformed_model_text_is_rejected_without_network(raw_model_text: str):
    from types import SimpleNamespace

    from gemini_service import GeminiAnalyzer, GeminiServiceError

    analyzer = object.__new__(GeminiAnalyzer)
    analyzer.model = "offline-test-only"
    analyzer.client = SimpleNamespace(
        models=SimpleNamespace(
            generate_content=lambda **_kwargs: SimpleNamespace(text=raw_model_text)
        )
    )
    with pytest.raises(GeminiServiceError) as caught:
        analyzer.analyze(b"test-bytes", "image/png", "A test claim")
    assert caught.value.status_code == 502
