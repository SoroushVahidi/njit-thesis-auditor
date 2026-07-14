# Evaluation review labels

Offline schema for recording human judgments on auditor findings (or known misses).
This is labeling infrastructure only — it does **not** change detectors, thresholds,
confidence, highlights, or web/report runtime output.

## Label vocabulary

- `true_positive`
- `false_positive`
- `false_negative`
- `correct_but_too_strict`
- `wrong_location`
- `wrong_highlight`
- `wrong_wording`
- `duplicate`
- `policy_decision_needed`

## Record shape

Required:

- `sample_id` — stable corpus ID (e.g. `ester_sample_b` or a synthetic demo ID).
  **Not** a filesystem path or PDF filename.
- `label` — one of the vocabulary values above.

Optional:

- `rule_id`
- `issue_type`
- `page`
- `finding_id` (prefer report anchors such as `problem-12`)
- `reviewer_note` — must not contain private dissertation body text, student names,
  or annotation contents.

## API

```python
from njit_auditor.review_labels import (
    validate_review_label_payload,
    validate_review_label_document,
)

label = validate_review_label_payload(
    {"sample_id": "synthetic_demo_a", "label": "true_positive", "rule_id": "P015"}
)
```

Unknown labels raise `ReviewLabelValidationError`.

## Example data

Synthetic-only example:

`tests/fixtures/review_labels/synthetic_example.json`

There is no requirement to label the existing evaluation corpus immediately.
