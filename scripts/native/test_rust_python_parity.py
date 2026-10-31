"""Offline contract parity: Rust telemetry candidate vs authoritative Python OS.

Run AFTER building the local Rust executable. No DB, documents, external API,
user data, remote inference, network or deployment.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import subprocess
import sys
import unittest

from ecoiq_os.process_diagnostic import (
    ProcessMeasurement, ProcessSnapshot, diagnose_process,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BIN = ROOT / "native/rust_resource_kernel/target/debug/ecoiq-resource-kernel"
RUST_BINARY = Path(os.environ.get("ECOIQ_RUST_CANDIDATE_BIN", str(DEFAULT_BIN)))


def python_diagnostic(input_value: float | None, loss_value: float | None):
    snapshot = ProcessSnapshot(
        case_id="SYNTH-NATIVE-1",
        domain="construction",
        process_name="Test goods handling",
        resource_type="material",
        input_measurement=ProcessMeasurement(
            value=input_value, unit="kg", period="2026-10",
            evidence_refs=("SYNTH-IN",),
        ),
        loss_measurement=ProcessMeasurement(
            value=loss_value, unit="kg", period="2026-10",
            evidence_refs=("SYNTH-LOSS",),
        ),
    )
    return diagnose_process(snapshot).to_dict()


def rust_diagnostic(input_value: float | None, loss_value: float | None):
    if not RUST_BINARY.is_file():
        raise FileNotFoundError(
            "Build the local Rust candidate before running parity tests."
        )
    def token(value):
        return "unknown" if value is None else str(value)
    cmd = [
        str(RUST_BINARY), "--input", token(input_value),
        "--loss", token(loss_value), "--unit", "kg",
        "--period", "2026-10",
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=5, check=True,
    )
    return json.loads(result.stdout)


class NativeParityTests(unittest.TestCase):
    def test_candidate_matches_existing_deterministic_python_boundary(self):
        for inp, loss in [
            (1000.0, 120.0),
            (1000.0, 0.0),
            (1000.0, None),
            (None, 20.0),
            (0.0, 0.0),
            (99999.0, 0.01),
            (12345.0, 67.89),
        ]:
            with self.subTest(inp=inp, loss=loss):
                canonical = python_diagnostic(inp, loss)
                candidate = rust_diagnostic(inp, loss)
                self.assertEqual(
                    candidate["loss_percent"] is None,
                    canonical["kpi"]["value"] is None,
                )
                if candidate["loss_percent"] is not None:
                    self.assertTrue(math.isclose(
                        candidate["loss_percent"], canonical["kpi"]["value"],
                        abs_tol=0.00005, rel_tol=0.0,
                    ))
                self.assertEqual(
                    candidate["status"], canonical["kpi"]["status"],
                )
                self.assertFalse(candidate["independently_verified"])
                self.assertFalse(candidate["implementation_permitted"])
                self.assertFalse(canonical["kpi"]["independently_verified"])
                self.assertTrue(canonical["next_step"]["next_stage"] == "COLLECT_EVIDENCE")

    def test_candidate_rejects_negative_or_loss_above_input(self):
        for inp, loss in [(-1, 0), (1, 2), (float("nan"), 1), (100, -2)]:
            with self.subTest(inp=inp, loss=loss):
                cmd = [
                    str(RUST_BINARY), "--input", str(inp),
                    "--loss", str(loss), "--unit", "kg",
                    "--period", "2026-10",
                ]
                out = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                self.assertNotEqual(out.returncode, 0)
                self.assertEqual(out.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
