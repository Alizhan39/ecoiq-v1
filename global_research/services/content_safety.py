"""
global_research/services/content_safety.py — external content is evidence,
never instruction. This is enforced STRUCTURALLY elsewhere in this app
(every source/claim text field is a plain TextField, rendered only through
Django's auto-escaping templates, never passed to a function capable of
taking an action) — this module adds an explicit, auditable detection step
on top, mirroring `legacy_safe`'s "evidence is templated, never executed"
philosophy and extending
`agent_runtime_model_router/services/safety_assertions.py`'s deterministic,
regex-based rule style rather than asking an LLM to judge intent.

Detecting an injection attempt never changes how the content is treated —
a flagged source is still stored as inert evidence, still visible in the
UI, still eligible for a human to read. Flagging exists only to surface the
attempt for review and logging, never to auto-reject or auto-anything.
"""
import logging
import re

logger = logging.getLogger('global_research.content_safety')

INJECTION_PATTERNS = [
    re.compile(r'ignore (all )?(previous|prior|above) instructions', re.I),
    re.compile(r'\bsystem note\b\s*:', re.I),
    re.compile(r'\byou are now\b', re.I),
    re.compile(r'disregard (all )?(previous|prior) (rules|instructions)', re.I),
    re.compile(r'act as (an?|the) (admin|system|root)', re.I),
    re.compile(r'\bmark (this|it) as approved\b', re.I),
    re.compile(r'\bapprove (this|it) (automatically|without (further )?review)\b', re.I),
    re.compile(r'\bshortlist(ed)? (this|it) (automatically|without review)\b', re.I),
]


def detect_injection_attempt(*texts):
    """Returns the list of matched pattern strings across all given text
    fragments. Empty list means clean — never raises, never mutates input."""
    matched = []
    for text in texts:
        if not text:
            continue
        for pattern in INJECTION_PATTERNS:
            if pattern.search(text) and pattern.pattern not in matched:
                matched.append(pattern.pattern)
    return matched


def classify_content(*texts):
    """Always classifies external text as 'evidence' — never 'instruction'
    — regardless of what it contains. The classification step exists so
    every caller makes this decision explicitly and auditably rather than
    implicitly trusting text by default."""
    matched = detect_injection_attempt(*texts)
    if matched:
        logger.warning('Prompt-injection-attempt pattern(s) detected in external content: %s', matched)
    return {
        'classification': 'evidence',
        'injection_attempt_detected': bool(matched),
        'matched_patterns': matched,
    }


def flag_source_if_suspicious(source):
    """Runs classify_content over a ResearchSource's own text fields and
    sets its content_safety_flagged/content_safety_notes fields. Called
    once at source-creation time by services/orchestrator.py — never
    re-derives trust from the flag itself (a flagged source is neither
    auto-rejected nor auto-downgraded in tier)."""
    result = classify_content(source.title, source.permitted_extract, source.licence_or_usage_note)
    if result['injection_attempt_detected']:
        source.content_safety_flagged = True
        source.content_safety_notes = (
            f'Injection-attempt pattern(s) detected: {result["matched_patterns"]}. '
            'Content is still treated as inert evidence — no action was taken automatically.'
        )
        source.save(update_fields=['content_safety_flagged', 'content_safety_notes', 'updated_at'])
    return result
