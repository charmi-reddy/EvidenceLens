# EvidenceLens evaluation (Phase 4)

## What this is—and is not

`data/cases.jsonl` is a small **controlled, synthetic, manually labelled test set**, not an external benchmark or a representative sample of real photographs. The local PNGs are deterministically drawn by `generate_images.py`. Expected claim verdicts were assigned by inspecting those simple drawings: visible matching details are supported, explicit absent objects are contradicted, and location/time claims are insufficient because the images contain no such metadata or cues. The hand-authored labels have not had independent annotator review.

The existing `fixtures/evidencelens-*.json` files are deterministic UI/schema fixtures only. They are not model predictions and are never used as scored outputs.

`data/historical-live-smoke.jsonl` contains **only two status observations** from prior actual HTTP 200 Gemini calls (supported and contradicted) and a separate actual HTTP 429 record for the location case. These statuses were transcribed from the earlier live checks; this phase made no Gemini calls. Full raw response bodies were not retained as files. The 429 record is a failed request, not an insufficient-evidence prediction. The mixed live case has no output record.

## Reproduce dataset images and local evaluation

From the repository root:

```bash
python -m venv .venv-eval
. .venv-eval/bin/activate
pip install -r evaluation/requirements.txt
python evaluation/generate_images.py
python evaluation/evaluate.py
```

The scorer makes no network requests. It joins observed claims to reference claims by exact `case_id` and claim text, scores successful HTTP 200 observations only, and reports per-class precision/recall/F1 plus a confusion matrix. Failed HTTP rows are counted but never treated as labels. Classes with no true or predicted observations are reported as `null` (unmeasured), not as zero performance.

To score a later, genuinely collected live run, write a separate JSONL predictions file with one record per case, for example:

```json
{"case_id":"red-circle-supported","http_status":200,"model":"<configured-model>","observed_claims":[{"text":"A red circle is visible in the image.","status":"supported"}]}
```

Then pass it with `python evaluation/evaluate.py --predictions path/to/actual-outputs.jsonl`. Do not copy expected labels or UI fixtures into that predictions file.

## Current scope/limitations

- 9 synthetic image-caption pairs, 15 manually assigned claim labels, 2 deterministic local images.
- Only 2 historical successful model claims are available for scoring: one supported and one contradicted. Their per-class scores are each based on **n=1** and are exploratory smoke checks, not a model-accuracy estimate.
- Insufficient-evidence live evaluation is blocked by HTTP 429; its precision/recall/F1 are unmeasured.
- Mixed multi-claim live evaluation has not been run; it is present only as labelled data and local aggregation/rendering tests.
- No external dataset, demographic/domain coverage, uncertainty calibration, or statistically meaningful confidence interval is provided.
