"""
One place that decides what "we do not know" does to a number.

EcoIQ has several parallel scoring engines — core EcoIQ scoring, ethics
(NEI/TSS/RVI), financing matching, QDF, ML. Each grew its own private helper
for turning a possibly-missing field into a float, and each got it wrong in its
own way:

    float(v or 0)          unknown -> 0     the WORST possible score
    value or 50            unknown -> 50    an invented average
    .get(category, 50.0)   unknown -> 50    an invented category
    mean(xs) if xs else 50 nothing  -> 50   an average of no observations

Two of those are also falsy-triggered, so they rewrote a genuine measured 0.0 as
well — turning the worst real observation a company could have into an average
one, or into the same value as no observation at all.

The D-programme fixed core scoring and financing first (#242). Fixing the next
engine by copying the corrected helper a fourth time would reproduce exactly the
condition that caused the divergence, so the corrected semantics live here
instead, importable by any engine:

    unknown stays unknown

`core` is the right home: it imports no models and belongs to no scoring domain,
so every engine can depend on it and none of them depend on each other. Nothing
here knows what a "pillar" or a "harm" is — the domain decides what to DO with
an unknown; this module only guarantees the unknown survives long enough to be
decided about.

Whether a partial result may be PUBLISHED is a separate question, owned by
companies.evidence and score eligibility (plan step D5). Do not answer it here.
"""
from __future__ import annotations


def known(value) -> float | None:
    """
    The value as a float if it is known, else None.

    Use in place of `x or 0` / `x or 50`. Note the difference that matters:
    `0.0 or 50` is 50, but `known(0.0)` is 0.0.
    """
    return None if value is None else float(value)


def clamp(value, lo: float = 0.0, hi: float = 100.0) -> float | None:
    """
    Bound a known value to [lo, hi]. Unknown stays unknown.

        clamp(None)  -> None
        clamp(0.0)   -> 0.0
        clamp(50.0)  -> 50.0
        clamp(120.0) -> 100.0
        clamp(-20.0) -> 0.0
    """
    if value is None:
        return None
    return max(lo, min(hi, float(value)))


def mean_of_known(*values) -> float | None:
    """
    Mean of the values that are actually known. None when none are.

    The deliberate choice, carried over from core scoring: average what is
    known rather than refusing the whole dimension. Evidence coverage already
    reports partiality separately, so refusing here would discard real
    information AND hide the gap.

    Values are clamped, so a caller cannot smuggle an out-of-range number in.

        mean_of_known(80, 60)     -> 70.0
        mean_of_known(80, None)   -> 80.0
        mean_of_known(0.0, 100.0) -> 50.0   (a real 0 counts)
        mean_of_known(None, None) -> None
        mean_of_known()           -> None
    """
    present = [c for c in (clamp(v) for v in values) if c is not None]
    return sum(present) / len(present) if present else None


def weighted_mean_of_known(*pairs) -> float | None:
    """
    Weighted mean over the known (value, weight) pairs, RE-NORMALISED.

    Re-normalisation is the whole point. Dropping an unknown term from a
    weighted sum without rescaling quietly shrinks the result, so a company
    missing one input scores lower than an identical company that has it —
    penalising it for the absence rather than for anything it did.

        weighted_mean_of_known((80, .4), (80, .35), (None, .25)) -> 80.0
        (not 80 * 0.75 = 60.0, which is the un-renormalised bug)

    None when nothing is known, or when the known weights sum to zero.
    """
    present = [(clamp(v), w) for v, w in pairs if v is not None]
    total_weight = sum(w for _, w in present)
    if not present or total_weight == 0:
        return None
    return sum(v * w for v, w in present) / total_weight


def format_known(value, spec: str = '.1f', absent: str = 'not assessed') -> str:
    """
    Render a possibly-unknown number for a human or a language model.

    D4A. Format specifiers are where unknown values crash — `f'{score:.1f}'`
    raises on None — and the reflex fix is to substitute a number so the string
    builds. That reflex is how `50` got into so much of this codebase.

    So the substitute is WORDS, not a number. A report that says
    "Public Benefit: not assessed" is honest; one that says
    "Public Benefit: 50.0" is a fabricated measurement, and neither the reader
    nor a language model reading it downstream can tell the difference.

    The distinction matters most in prompts. An LLM handed "50.0" will reason
    about an average company and write fluent, confident prose about a
    measurement nobody made.
    """
    if value is None:
        return absent
    try:
        return format(float(value), spec)
    except (TypeError, ValueError):
        return absent
