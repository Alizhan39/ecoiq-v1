"""
agent_runtime_model_router/services/schema_validation.py — Structured Output
Validation.

Checks required keys, data types, enums, confidence range, evidence
references, missing-data visibility and the approval field. Invalid output
is never silently "fixed" — the caller (execution.py) stores the raw and
parsed output exactly as produced, marks `schema_valid=False`, and refuses
to let it enter Council reasoning as a trusted position.

Real `ai_agents/*/test_cases.json` fixtures are often partial (e.g. a golden
case asserting only `human_approval_required`, with no `confidence` or
`status`) — this validator's required-field set is deliberately the small,
honest minimum a governed decision actually needs, not the full canonical
field list. Partial replays failing validation is a feature, not a bug: it
proves the gate is real.
"""
REQUIRED_FIELDS = ['confidence', 'human_approval_required', 'status']
STATUS_ENUM = {'completed', 'blocked', 'needs_review'}


def validate_agent_output(parsed_output, expected_schema=None):
    """Returns (valid: bool, errors: list[str])."""
    errors = []
    required_fields = (expected_schema or {}).get('required_fields', REQUIRED_FIELDS)

    for field_name in required_fields:
        if field_name not in parsed_output:
            errors.append(f"Missing required field: '{field_name}'")

    if 'confidence' in parsed_output:
        confidence = parsed_output['confidence']
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            errors.append("'confidence' must be numeric")
        elif not (0 <= confidence <= 100):
            errors.append("'confidence' must be within 0-100")

    if 'human_approval_required' in parsed_output:
        if not isinstance(parsed_output['human_approval_required'], bool):
            errors.append("'human_approval_required' must be a boolean")

    if 'status' in parsed_output:
        status = parsed_output['status']
        if status not in STATUS_ENUM:
            errors.append(f"'status' must be one of {sorted(STATUS_ENUM)}, got {status!r}")

    for list_field in ('risk_flags', 'evidence_used', 'missing_data'):
        if list_field in parsed_output and not isinstance(parsed_output[list_field], list):
            errors.append(f"'{list_field}' must be a list")

    if 'next_action' in parsed_output and not isinstance(parsed_output['next_action'], str):
        errors.append("'next_action' must be a string")

    return len(errors) == 0, errors
