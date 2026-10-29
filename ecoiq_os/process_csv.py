"""Strict local CSV adapter for reported business process observations.

The adapter accepts one process/resource/period per CSV file, aggregates
reported input and loss, and reuses EcoIQ's evidence-aware diagnostic.
It has no HTTP endpoint, database write, remote fetch or tenant bypass.
It does not authenticate sources: evidence_ref values remain unverified labels.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from io import StringIO
from pathlib import Path

from ecoiq_os.process_diagnostic import (
    ProcessMeasurement,
    ProcessSnapshot,
    diagnose_process,
)

MAX_CSV_BYTES = 512 * 1024
MAX_ROWS = 1000
MAX_QUANTITY = Decimal("999999999999")
FIELDS = (
    "record_id", "case_id", "domain", "process_name", "resource_type",
    "period", "unit", "flow_type", "quantity", "evidence_ref",
)
CASE_FIELDS = ("case_id", "domain", "process_name", "resource_type", "period", "unit")
FLOW_TYPES = ("input", "loss")
_QUANTITY = re.compile(r"(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,4})?\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}\Z")
_PERIOD = re.compile(r"[0-9]{4}-(?:0[1-9]|1[0-2])\Z")


@dataclass(frozen=True)
class CSVImportSummary:
    snapshot: ProcessSnapshot
    row_count: int
    # For audit clarity, an unknown row makes that entire flow total unknown.
    unknown_inputs: int
    unknown_losses: int


def _text(value: str, field: str, line: int, max_length: int = 128) -> str:
    value = value.strip()
    if not value or len(value) > max_length or any(ord(char) < 32 for char in value):
        raise ValueError(f"Invalid {field} on CSV row {line}.")
    return value


def _quantity(raw: str, line: int) -> Decimal | None:
    raw = raw.strip()
    if not raw:
        return None
    if not _QUANTITY.fullmatch(raw):
        raise ValueError(f"Invalid quantity on CSV row {line}; use a non-negative decimal.")
    try:
        amount = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid quantity on CSV row {line}.") from exc
    if amount > MAX_QUANTITY:
        raise ValueError(f"Quantity exceeds supported maximum on CSV row {line}.")
    return amount


def parse_process_csv(text: str) -> CSVImportSummary:
    """Parse a bounded, single-process CSV without accepting mixed units/scopes.

    A blank quantity is missing data, not a zero. Missing any one quantity in
    a flow makes that aggregate unknown; we never sum only the known subset.
    Every known quantity must have a source reference, but identifiers are not
    proof that the source was reviewed or exists.
    """
    if not isinstance(text, str):
        raise TypeError("CSV content must be decoded UTF-8 text.")
    if len(text.encode("utf-8")) > MAX_CSV_BYTES:
        raise ValueError("CSV exceeds maximum allowed size.")
    reader = csv.reader(StringIO(text.lstrip("\ufeff"), newline=""), strict=True)
    try:
        header = next(reader)
    except (StopIteration, csv.Error) as exc:
        raise ValueError("Missing or malformed CSV header.") from exc
    if len(header) != len(FIELDS) or len(set(header)) != len(FIELDS) or set(header) != set(FIELDS):
        raise ValueError("CSV columns must match the documented schema exactly.")
    index = {key: header.index(key) for key in FIELDS}
    context: tuple[str, ...] | None = None
    seen: set[str] = set()
    totals = {flow: Decimal("0") for flow in FLOW_TYPES}
    refs: dict[str, list[str]] = {flow: [] for flow in FLOW_TYPES}
    unknown = {flow: 0 for flow in FLOW_TYPES}
    row_count = 0
    flow_counts = {flow: 0 for flow in FLOW_TYPES}

    try:
        for line, cells in enumerate(reader, start=2):
            if not cells:  # Blank physical lines are harmless.
                continue
            row_count += 1
            if row_count > MAX_ROWS:
                raise ValueError(f"CSV exceeds {MAX_ROWS} observation rows.")
            if len(cells) != len(FIELDS):
                raise ValueError(f"Wrong number of columns on CSV row {line}.")
            row = dict(zip(header, cells, strict=True))
            record_id = _text(row["record_id"], "record_id", line)
            if not _ID.fullmatch(record_id):
                raise ValueError(f"Invalid record_id on CSV row {line}.")
            if record_id in seen:
                raise ValueError(f"Duplicate record_id on CSV row {line}.")
            seen.add(record_id)
            group = tuple(_text(row[key], key, line) for key in CASE_FIELDS)
            if not _ID.fullmatch(group[0]):
                raise ValueError(f"Invalid case_id on CSV row {line}.")
            if not _PERIOD.fullmatch(group[4]):
                raise ValueError(f"Invalid period on CSV row {line}; use YYYY-MM.")
            if context is None:
                context = group
            elif group != context:
                raise ValueError(f"Mixed process, unit, domain or period on CSV row {line}.")
            flow = _text(row["flow_type"], "flow_type", line)
            if flow not in FLOW_TYPES:
                raise ValueError(f"Unsupported flow_type on CSV row {line}.")
            flow_counts[flow] += 1
            amount = _quantity(row["quantity"], line)
            ref = row["evidence_ref"].strip()
            if ref and (len(ref) > 128 or not _ID.fullmatch(ref)):
                raise ValueError(f"Invalid evidence_ref on CSV row {line}.")
            if amount is not None and not ref:
                raise ValueError(f"Known quantity requires evidence_ref on CSV row {line}.")
            if ref and ref not in refs[flow]:
                refs[flow].append(ref)
            if amount is None:
                unknown[flow] += 1
            else:
                totals[flow] += amount
                if totals[flow] > MAX_QUANTITY:
                    raise ValueError(f"Aggregate {flow} exceeds supported maximum.")
    except csv.Error as exc:
        raise ValueError("Malformed CSV quoting or record structure.") from exc

    if context is None:
        raise ValueError("CSV has no observations.")
    case_id, domain, process, resource, period, unit = context
    def measure(flow: str) -> ProcessMeasurement:
        quantity = float(totals[flow]) if flow_counts[flow] and not unknown[flow] else None
        return ProcessMeasurement(
            value=quantity,
            unit=unit,
            period=period,
            evidence_refs=tuple(refs[flow]),
        )

    snapshot = ProcessSnapshot(
        case_id=case_id,
        domain=domain,
        process_name=process,
        resource_type=resource,
        input_measurement=measure("input"),
        loss_measurement=measure("loss"),
    )
    return CSVImportSummary(snapshot, row_count, unknown["input"], unknown["loss"])


def diagnose_csv(text: str) -> dict:
    """Return diagnostics from reported observations, with no write operations."""
    imported = parse_process_csv(text)
    result = diagnose_process(imported.snapshot).to_dict()
    result["import"] = {
        "format": "process_csv_v1",
        "rows": imported.row_count,
        "unknown_inputs": imported.unknown_inputs,
        "unknown_losses": imported.unknown_losses,
        "source_authentication": "NOT_VERIFIED",
        "data_persisted": False,
    }
    return result


def main(argv: list[str] | None = None) -> int:
    """Opt-in local inspection; outputs no row contents or document identifiers."""
    parser = argparse.ArgumentParser(description="EcoIQ read-only process CSV inspector")
    parser.add_argument("--input", required=True, type=Path, help="Local UTF-8 CSV file")
    args = parser.parse_args(argv)
    with args.input.open("rb") as handle:
        data = handle.read(MAX_CSV_BYTES + 1)
    if len(data) > MAX_CSV_BYTES:
        parser.error("CSV exceeds maximum allowed size.")
    try:
        result = diagnose_csv(data.decode("utf-8-sig"))
    except (UnicodeError, ValueError) as exc:
        parser.error(str(exc))
    # Intentionally omit company names, process names, source IDs and raw flows.
    print(json.dumps({
        "read_only": True,
        "kpi": {
            "key": result["kpi"]["key"],
            "value": result["kpi"]["value"],
            "status": result["kpi"]["status"],
        },
        "next_stage": result["next_step"]["next_stage"],
        "rows": result["import"]["rows"],
        "source_authentication": "NOT_VERIFIED",
        "data_persisted": False,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
