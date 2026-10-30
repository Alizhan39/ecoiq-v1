"""A single synthetic EcoIQ situation report using Rust, C++ and Python.

Read-only, no Django DB access, no client files, no AI/provider calls.
Requires local binaries built from this checked-out repository.
Uses Rust CLI and C++ CLI for *illustration*, NOT a fast production FFI.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ecoiq_os.decision_islah import build_preliminary_brief  # noqa: E402
from ecoiq_os.situation_guidance import assemble_situation_guidance  # noqa: E402


def _invoke(binary: Path, arguments: list[str]) -> dict:
    if not binary.is_file():
        raise RuntimeError("Build offline native demo binaries before running this example.")
    result = subprocess.run(
        [str(binary), *arguments], capture_output=True, text=True,
        timeout=5, check=True,
    )
    parsed = json.loads(result.stdout)
    if not isinstance(parsed, dict):
        raise RuntimeError("Native demo output was not a JSON object.")
    return parsed


def run_synthetic_native_demo(
    *, rust_binary: Path | None = None, cpp_binary: Path | None = None,
) -> dict:
    rust_binary = rust_binary or Path(os.environ.get(
        "ECOIQ_RUST_CANDIDATE_BIN",
        str(ROOT / "native/rust_resource_kernel/target/debug/ecoiq-resource-kernel"),
    ))
    cpp_binary = cpp_binary or Path(os.environ.get(
        "ECOIQ_CPP_CANDIDATE_BIN",
        str(ROOT / "native/cpp_twin_geometry/target/ecoiq-twin-preview"),
    ))
    # All fixture quantities are fictional, and intentionally bounded.
    brief = build_preliminary_brief(
        case_id="OFFLINE-SYNTH-1", domain="construction",
        process_name="Fictional material handling", resource_type="material",
        period="2026-10", unit="kg",
        reported_input=1000.0, reported_loss=120.0,
    )
    guidance = assemble_situation_guidance(brief)
    rust = _invoke(rust_binary, [
        "--input", "1000", "--loss", "120",
        "--unit", "kg", "--period", "2026-10",
    ])
    cpp = _invoke(cpp_binary, ["2", "3", "4", "2"])
    py_value = guidance["formulas"][0]["value"]
    native_value = rust.get("loss_percent")
    if (not isinstance(native_value, (float, int))
            or not math.isclose(native_value, py_value, abs_tol=0.00005)):
        raise RuntimeError("Rust reported KPI diverges from the Python authority.")
    if rust.get("independently_verified") is not False:
        raise RuntimeError("Rust cannot upgrade evidence to independently verified.")
    if rust.get("implementation_permitted") is not False:
        raise RuntimeError("Rust cannot approve business interventions.")
    if cpp.get("engineering_calibrated") is not False:
        raise RuntimeError("Synthetic geometry is never engineering calibrated.")
    volume = cpp.get("synthetic_geometry_volume_m3")
    if not isinstance(volume, (float, int)) or not math.isclose(volume, 192.0):
        raise RuntimeError("C++ synthetic geometry calibration fixture is invalid.")
    return {
        "scenario": "fictional_construction_resource_and_geometry",
        "native_rust": rust,
        "native_cpp": cpp,
        "python_situation": {
            "status": guidance["situation"],
            "formula_results": guidance["formulas"],
            "next_step": guidance["next_step"],
            "quran_research_locators": [
                {"concept": item["concept"],
                 "references": [ref["locator"] for ref in item["references"]],
                 "review_state": item["review_state"]}
                for item in guidance["guidance_lenses"]
            ],
        },
        "checks": {
            "rust_python_formula_parity": True,
            "site_data_used": False,
            "quran_text_used_for_training": False,
            "generative_ai_called": False,
            "human_decision_recorded": False,
            "operational_intervention_permitted": False,
            "ready_for_commercial_production": False,
        },
    }


def main() -> int:
    try:
        result = run_synthetic_native_demo()
    except (RuntimeError, subprocess.SubprocessError, ValueError) as exc:
        print("Offline synthetic demo failed: " + str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
