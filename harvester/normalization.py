"""
EcoIQ Evidence Harvester — Normalization Engine (Slice 3, additive, deterministic).

Converts verified Evidence text into structured Datapoints using regex/keyword
rules ONLY — no AI, no inference, no fabrication. When a metric is discussed but
no clean value can be parsed, a NOT_NORMALIZED Datapoint is recorded with
value=None rather than guessing.

  "Scope 1 emissions reduced by 12%"  →  scope1_emissions_change = -12 percent
  "Gross revenue was £18,378m"        →  revenue = 18378 GBP_million
  "Scope 1 emissions were 4.5 MtCO2e" →  scope1_emissions = 4.5 MtCO2e
  "emissions fell significantly"      →  scope*_emissions = None  (NOT_NORMALIZED)

These Datapoints are inert facts. They power later engines (Governance,
Planetary Balance, Future Generations, Moral Compass, Executive Brief) — none of
which are built here.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

# ── Metric specifications (the 21 required metrics) ─────────────────────────
# Each: metric slug, category, and the keyword phrases that signal the metric is
# being discussed. Keywords are matched as lowercase substrings.
@dataclass(frozen=True)
class MetricSpec:
    metric: str
    category: str
    keywords: tuple


METRICS = [
    # Financial
    MetricSpec("revenue", "financial", ("gross revenue", "total revenue", "revenue", "turnover")),
    MetricSpec("operating_profit", "financial", ("operating profit", "underlying operating profit")),
    MetricSpec("net_profit", "financial", ("net profit", "profit after tax", "profit for the year")),
    MetricSpec("capex", "capital_projects", ("capital expenditure", "capital investment", "capex")),
    MetricSpec("opex", "financial", ("operating expenditure", "operating expenses", "operating costs", "opex")),
    # Energy
    MetricSpec("renewable_generation", "energy", ("renewable generation", "renewable energy generated", "renewable electricity")),
    MetricSpec("coal_generation", "energy", ("coal generation", "coal-fired generation", "generation from coal")),
    MetricSpec("gas_generation", "energy", ("gas generation", "gas-fired generation", "generation from gas")),
    MetricSpec("energy_generated", "energy", ("energy generated", "electricity generated", "total generation", "power generated")),
    # Climate
    MetricSpec("scope1_emissions", "emissions", ("scope 1",)),
    MetricSpec("scope2_emissions", "emissions", ("scope 2",)),
    MetricSpec("scope3_emissions", "emissions", ("scope 3",)),
    MetricSpec("emissions_intensity", "emissions", ("emissions intensity", "carbon intensity", "co2 intensity")),
    # Water
    MetricSpec("water_withdrawal", "water", ("water withdrawal", "water withdrawn", "water abstraction", "water abstracted")),
    MetricSpec("water_consumption", "water", ("water consumption", "water consumed")),
    # Workforce
    MetricSpec("lost_time_incidents", "health_safety", ("lost time incident", "lost-time injury", "lost time injury", "ltifr")),
    MetricSpec("employee_count", "workforce", ("employees", "headcount", "number of employees", "workforce of")),
    # Governance
    MetricSpec("independent_directors_percent", "governance", ("independent directors", "board independence")),
    MetricSpec("board_size", "governance", ("board comprises", "board of directors", "members of the board", "directors on the board")),
]

# ── Direction (for change statements) ───────────────────────────────────────
_DECREASE = ("reduced", "decreased", "decrease", "fell", "lower", "cut by", "down by", "decline", "reduction")
_INCREASE = ("increased", "increase", "rose", "grew", "higher", "up by", "growth")

# ── Number + unit parsing ───────────────────────────────────────────────────
# number (with thousands separators / decimals) + optional trailing unit token.
_NUM = r"(\d[\d,]*(?:\.\d+)?)"
_PERCENT_RE = re.compile(_NUM + r"\s*(?:%|per cent|percent)", re.I)
_QTY_RE = re.compile(
    _NUM + r"\s*"
    r"(mtco2e|ktco2e|tco2e|gco2/kwh|kgco2e|twh|gwh|mwh|megalitres|ml|m3|"
    r"billion|bn|million|m|thousand|k|employees|people|directors)?",
    re.I,
)
_YEAR_RE = re.compile(r"\b(20\d{2})(?:/(\d{2}))?\b")

_UNIT_NORMAL = {
    "mtco2e": "MtCO2e", "ktco2e": "ktCO2e", "tco2e": "tCO2e", "kgco2e": "kgCO2e",
    "gco2/kwh": "gCO2/kWh",
    "twh": "TWh", "gwh": "GWh", "mwh": "MWh",
    "megalitres": "ML", "ml": "ML", "m3": "m3",
    "billion": "billion", "bn": "billion", "million": "million", "m": "million",
    "thousand": "thousand", "k": "thousand",
    "employees": "count", "people": "count", "directors": "count",
}

# Confidence by extraction certainty (extraction certainty, not company truth).
CONF_CHANGE = 0.90       # metric + direction + clean percentage
CONF_ABSOLUTE = 0.85     # metric + clean number + unit
CONF_NO_VALUE = 0.30     # metric present, no parseable number → NOT_NORMALIZED
LOW_CONFIDENCE = 0.50    # below this → NOT_NORMALIZED


@dataclass
class RawDatapoint:
    metric: str
    category: str
    value: Optional[float]
    unit: str
    period: str
    period_year: Optional[int]
    confidence: float
    status: str


def _to_float(num_str: str) -> Optional[float]:
    try:
        return float(num_str.replace(",", ""))
    except (ValueError, AttributeError):
        return None


def _detect_period(text: str):
    m = _YEAR_RE.search(text or "")
    if not m:
        return "", None
    label = m.group(0)               # e.g. "2024/25" or "2025"
    start = int(m.group(1))
    if m.group(2):                   # "2024/25" → fiscal year ENDING 2025
        year = (start // 100) * 100 + int(m.group(2))
    else:
        year = start
    return label, year


def _direction_sign(text: str) -> Optional[int]:
    t = text.lower()
    down = any(k in t for k in _DECREASE)
    up = any(k in t for k in _INCREASE)
    if down and not up:
        return -1
    if up and not down:
        return 1
    return None


def _currency_prefixed(text: str, unit: str) -> str:
    """Prefix GBP_ for million/billion magnitudes stated in pounds."""
    if unit in ("million", "billion") and ("£" in text or "gbp" in text.lower()):
        return "GBP_" + unit
    return unit


def extract(text: str) -> list[RawDatapoint]:
    """Deterministically extract datapoints from a piece of evidence text.

    One datapoint per matched metric (first clean match wins). Metrics that are
    mentioned but unparseable yield a NOT_NORMALIZED row (value=None)."""
    if not text:
        return []
    lower = text.lower()
    period, period_year = _detect_period(text)
    out = []
    seen = set()

    for spec in METRICS:
        if spec.metric in seen:
            continue
        if not any(k in lower for k in spec.keywords):
            continue
        seen.add(spec.metric)

        sign = _direction_sign(text)
        pct = _PERCENT_RE.search(text)

        # (a) change statement: direction + percentage → metric_change
        if sign is not None and pct:
            val = _to_float(pct.group(1))
            if val is not None:
                out.append(RawDatapoint(
                    metric=spec.metric + "_change", category=spec.category,
                    value=sign * val, unit="percent", period=period,
                    period_year=period_year, confidence=CONF_CHANGE,
                    status="NORMALIZED"))
                continue

        # (b) percentage metric without direction (e.g. independent directors %)
        if pct and spec.metric in ("independent_directors_percent",):
            val = _to_float(pct.group(1))
            if val is not None:
                out.append(RawDatapoint(
                    metric=spec.metric, category=spec.category, value=val,
                    unit="percent", period=period, period_year=period_year,
                    confidence=CONF_ABSOLUTE, status="NORMALIZED"))
                continue

        # (c) absolute quantity: first number carrying a RECOGNIZED unit.
        # Requiring a unit prevents misreading metric-label digits ("Scope 1")
        # or reporting years ("2024/25") as values — and avoids fabrication.
        chosen = None
        for qm in _QTY_RE.finditer(text):
            tok = (qm.group(2) or "").lower()
            norm = _UNIT_NORMAL.get(tok, "")
            if norm and _to_float(qm.group(1)) is not None:
                chosen = (_to_float(qm.group(1)), _currency_prefixed(text, norm))
                break
        if chosen is not None:
            out.append(RawDatapoint(
                metric=spec.metric, category=spec.category,
                value=chosen[0], unit=chosen[1], period=period,
                period_year=period_year, confidence=CONF_ABSOLUTE,
                status="NORMALIZED"))
            continue

        # (d) metric present but no parseable value → NOT_NORMALIZED (no fabrication)
        out.append(RawDatapoint(
            metric=spec.metric, category=spec.category, value=None, unit="",
            period=period, period_year=period_year, confidence=CONF_NO_VALUE,
            status="NOT_NORMALIZED"))

    return out


def normalize_evidence(evidence, *, save=True) -> list:
    """Extract Datapoints from an Evidence row and persist them (idempotent on
    evidence+metric+period). Returns the list of Datapoint instances."""
    from .models import Datapoint

    text = evidence.full_text or evidence.excerpt or evidence.title or ""
    results = extract(text)
    now = datetime.now(timezone.utc)
    points = []

    for r in results:
        status = r.status
        if r.value is None or r.confidence < LOW_CONFIDENCE:
            status = "NOT_NORMALIZED"
        defaults = {
            "company": getattr(evidence, "company", None),
            "value": r.value,
            "unit": r.unit,
            "period_year": r.period_year,
            "category": r.category or evidence.category,
            "confidence": round(r.confidence, 4),
            "status": status,
            "extraction_method": "deterministic-regex",
            "normalized_at": now,
        }
        if save and evidence.pk:
            dp, _ = Datapoint.objects.update_or_create(
                evidence=evidence, company_slug=evidence.company_slug,
                metric=r.metric, period=r.period, defaults=defaults,
            )
        else:
            dp = Datapoint(evidence=evidence, company_slug=evidence.company_slug,
                           metric=r.metric, period=r.period, **defaults)
        points.append(dp)

    return points
