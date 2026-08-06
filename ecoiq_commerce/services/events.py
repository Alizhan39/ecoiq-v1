"""
Commercial event tracking (PART 13). track_event() is the only way
CommercialEvent rows get created — it allow-lists which metadata keys are
storable so a call site can never accidentally dump raw report content,
portfolio holdings, or other private data into an analytics row. Anything
outside the allow-list is silently dropped, not stored — fail closed on
privacy, not on functionality.
"""
from ecoiq_commerce.models import COMMERCIAL_EVENT_TYPES, CommercialEvent

# Scalar-only, non-identifying-content fields. No free text, no report
# bodies, no portfolio holdings/notes, no evidence text.
_ALLOWED_METADATA_KEYS = {
    'plan_key', 'feature_key', 'amount', 'currency', 'api_key_prefix',
    'report_type', 'course_key', 'previous_plan_key', 'reason',
}


def track_event(event_type: str, *, user=None, organisation=None, product=None, plan=None, metadata=None):
    if event_type not in COMMERCIAL_EVENT_TYPES:
        raise ValueError(f'Unknown commercial event_type: {event_type!r}')

    clean_metadata = {}
    for key, value in (metadata or {}).items():
        if key not in _ALLOWED_METADATA_KEYS:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            clean_metadata[key] = value if not isinstance(value, str) else value[:200]

    return CommercialEvent.objects.create(
        event_type=event_type, user=user, organisation=organisation,
        product=product, plan=plan, metadata=clean_metadata,
    )
