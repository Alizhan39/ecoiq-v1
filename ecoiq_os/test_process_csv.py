"""Local CSV ingestion tests. All identifiers and numbers are fictional."""
from __future__ import annotations

import io
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest import TestCase

from ecoiq_os.kernel import COLLECT_EVIDENCE
from ecoiq_os.process_csv import (
    FIELDS, MAX_CSV_BYTES, MAX_ROWS,
    diagnose_csv, main, parse_process_csv,
)


def row(
    record_id="R001", flow_type="input", quantity="1000",
    evidence_ref="DOC-001", case_id="PILOT-001",
    domain="construction", process_name="Materials",
    resource_type="material", period="2026-10", unit="kg",
):
    item = dict(
        record_id=record_id, case_id=case_id, domain=domain,
        process_name=process_name, resource_type=resource_type,
        period=period, unit=unit, flow_type=flow_type,
        quantity=quantity, evidence_ref=evidence_ref,
    )
    return ",".join(item[name] for name in FIELDS)


HEADER = ",".join(FIELDS)


def csv_text(*rows):
    return "\n".join((HEADER, *rows, ""))


class ProcessCSVTests(TestCase):
    def test_csv_totals_feed_existing_os_kernel(self):
        data = csv_text(
            row("I1", "input", "600", "PO-001"),
            row("I2", "input", "400", "PO-002"),
            row("L1", "loss", "90", "WASTE-001"),
            row("L2", "loss", "30", "WASTE-002"),
        )
        result = diagnose_csv(data)
        self.assertEqual(result["kpi"]["value"], 12.0)
        self.assertEqual(result["kpi"]["numerator"], 120.0)
        self.assertEqual(result["kpi"]["denominator"], 1000.0)
        self.assertEqual(result["import"]["rows"], 4)
        self.assertEqual(result["next_step"]["next_stage"], COLLECT_EVIDENCE)
        self.assertEqual(
            result["kpi"]["evidence_refs"],
            ["PO-001", "PO-002", "WASTE-001", "WASTE-002"],
        )
        self.assertFalse(result["kpi"]["independently_verified"])
        self.assertFalse(result["import"]["data_persisted"])

    def test_bom_and_reordered_header(self):
        labels = list(reversed(FIELDS))
        record1 = dict(zip(FIELDS, row("I1").split(","), strict=True))
        record2 = dict(zip(FIELDS, row("L1", "loss", "0", "WASTE-0").split(","), strict=True))
        data = "\ufeff" + ",".join(labels) + "\n"
        data += ",".join(record1[key] for key in labels) + "\n"
        data += ",".join(record2[key] for key in labels) + "\n"
        self.assertEqual(diagnose_csv(data)["kpi"]["value"], 0)

    def test_missing_quantity_makes_whole_side_unknown(self):
        data = csv_text(
            row("I1", "input", "1000", "INV-1"),
            row("L1", "loss", "50", "WASTE-1"),
            row("L2", "loss", "", ""),
        )
        result = diagnose_csv(data)
        self.assertIsNone(result["kpi"]["value"])
        self.assertEqual(result["import"]["unknown_losses"], 1)
        self.assertIsNone(result["kpi"]["numerator"])

    def test_missing_whole_loss_flow_is_unknown(self):
        result = diagnose_csv(csv_text(row()))
        self.assertIsNone(result["kpi"]["numerator"])
        self.assertIsNone(result["kpi"]["value"])

    def test_zero_reported_input_yields_null_rate(self):
        result = diagnose_csv(csv_text(
            row("I1", "input", "0", "ZERO-IN"),
            row("L1", "loss", "0", "ZERO-LOSS"),
        ))
        self.assertIsNone(result["kpi"]["value"])
        self.assertEqual(result["kpi"]["numerator"], 0.0)

    def test_different_case_id_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Mixed process"):
            parse_process_csv(csv_text(
                row("I1", "input"),
                row("L1", "loss", "20", "WASTE", case_id="OTHER-CASE"),
            ))

    def test_different_period_or_unit_is_rejected(self):
        for change in ({"period": "2026-09"}, {"unit": "tonne"}):
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "Mixed process"):
                parse_process_csv(csv_text(
                    row("I1", "input"),
                    row("L1", "loss", "1", "WASTE", **change),
                ))

    def test_duplicate_id_does_not_double_count(self):
        with self.assertRaisesRegex(ValueError, "Duplicate record_id"):
            parse_process_csv(csv_text(
                row("I1", "input"),
                row("I1", "loss", "1", "WASTE"),
            ))

    def test_rejects_unreferenced_measurement(self):
        with self.assertRaisesRegex(ValueError, "requires evidence_ref"):
            parse_process_csv(csv_text(row("I1", "input", "5", "")))

    def test_rejects_bad_numeric_literals(self):
        for number in ("nan", "Infinity", "-1", "1e6", "1,000", "=SUM(A1:A2)", "9999999999999"):
            with self.subTest(number=number), self.assertRaises(ValueError):
                parse_process_csv(csv_text(row(quantity=number)))

    def test_rejects_loss_exceeding_input(self):
        with self.assertRaisesRegex(ValueError, "cannot exceed"):
            parse_process_csv(csv_text(
                row("I1", "input", "100", "IN"),
                row("L1", "loss", "101", "OUT"),
            ))

    def test_rejects_empty_headers_unknown_fields_and_missing_cells(self):
        for content in (
            "",
            "wrong,header\n1,2\n",
            HEADER + ",other\n",
            csv_text("just,one,cell"),
            HEADER + "\n",
            HEADER + "\n" + ",".join("x" for _ in range(len(FIELDS) + 1)),
        ):
            with self.subTest(content=content[:28]), self.assertRaises(ValueError):
                parse_process_csv(content)

    def test_rejects_malformed_quoting(self):
        with self.assertRaises(ValueError):
            parse_process_csv(HEADER + '\n"unfinished\n')

    def test_rejects_missing_evidence_status_override(self):
        # The CSV format contains no fields for Mizan or causal permission.
        self.assertNotIn("hypothesis_status", FIELDS)
        self.assertNotIn("mizan", FIELDS)
        self.assertNotIn("verified", FIELDS)

    def test_deny_oversized_files_and_too_many_rows(self):
        with self.assertRaisesRegex(ValueError, "size"):
            parse_process_csv("x" * (MAX_CSV_BYTES + 1))
        too_many = csv_text(*(
            row(f"I{i}", "input", "1", f"DOC-{i}") for i in range(MAX_ROWS + 1)
        ))
        with self.assertRaisesRegex(ValueError, "observation rows"):
            parse_process_csv(too_many)

    def test_local_cli_omits_sensitive_identifiers(self):
        data = csv_text(
            row("I1", "input", "100", "PRIVATE-DOC-1", case_id="PRIVATE-CASE"),
            row("L1", "loss", "10", "PRIVATE-DOC-2", case_id="PRIVATE-CASE"),
        )
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "input.csv"
            filename.write_text(data, encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["--input", str(filename)]), 0)
            self.assertIn('"value": 10.0', output.getvalue())
            self.assertNotIn("PRIVATE", output.getvalue())
            self.assertIn('"data_persisted": false', output.getvalue())

    def test_unknown_reference_is_not_treated_as_authentication(self):
        result = diagnose_csv(csv_text(
            row("I1", "input", "100", "CLAIMED-DOC"),
            row("L1", "loss", "20", "CLAIMED-LOSS"),
        ))
        self.assertEqual(result["import"]["source_authentication"], "NOT_VERIFIED")
        self.assertFalse(result["kpi"]["independently_verified"])
