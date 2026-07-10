"""
capital_guardian/services/audit_log.py — writes AuditLogEntry rows. Called
only from capital_guardian/signals.py's pre_save/post_save handlers, so
every entry reflects a real field change that actually happened in the
database — never a hand-authored narrative.

Honest terminology only: this is "Audit History"/"Change History", not a
claim of cryptographic immutability or blockchain verification.
"""
from capital_guardian.models import AuditLogEntry


def record_change(project, event_type, object_description, field_name, previous_value, new_value,
                   changed_by=None, source_reference='', approval_status=''):
    if previous_value == new_value:
        return None
    return AuditLogEntry.objects.create(
        project=project, event_type=event_type, object_description=object_description, field_name=field_name,
        previous_value='' if previous_value is None else str(previous_value),
        new_value='' if new_value is None else str(new_value),
        changed_by=changed_by, source_reference=source_reference, approval_status=approval_status,
    )


def record_creation(project, event_type, object_description, source_reference='', changed_by=None):
    return AuditLogEntry.objects.create(
        project=project, event_type=event_type, object_description=object_description,
        field_name='(created)', previous_value='', new_value='Created',
        changed_by=changed_by, source_reference=source_reference,
    )
