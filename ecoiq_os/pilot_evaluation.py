"""Stage 8 deterministic synthetic pilot benchmark — NO external model calls.

Measures only strict parser/citation boundary. The benchmark intentionally
documents semantic limitations; it is NOT LLM accuracy, data privacy
compliance, hallucination rate, or authorisation for actual interventions.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from ecoiq_os.grounded_ai import GroundedSource, validate_grounded_questions


@dataclass(frozen=True)
class Case:
    key: str
    output: str
    expected_status: str


SOURCE_TEXT = (
    "Synthetic goods receipt records 1000 kg on 2026-10-10. "
    "No independent measurement of avoidable loss exists."
)


def _output(question: str, quote: str = "receipt records 1000 kg",
            key: str = "S1", **extra) -> str:
    payload = {"questions": [{
        "question": question,
        "citations": [{"key": key, "quote": quote}],
    }]}
    payload.update(extra)
    return json.dumps(payload, ensure_ascii=False)


def synthetic_pilot_benchmark() -> dict[str, object]:
    source = (GroundedSource(
        key="S1", memory_id=101, excerpt=SOURCE_TEXT,
        review_tier="independently_verified", content_sha256="a" * 64,
    ),)
    question = "Could a stock cutoff explain the reported discrepancy?"
    accepted = "REVIEW_REQUIRED"
    rejected = "MODEL_OUTPUT_REJECTED"
    cases = (
        Case("cited_english_question", _output(question), accepted),
        Case("cited_russian_question", _output("Могла ли дата учёта объяснить расхождение?"), accepted),
        Case("cited_arabic_question", _output("هل يمكن أن يفسر توقيت الجرد هذا الفرق?"), accepted),
        Case("unknown_reference", _output(question, key="S9"), rejected),
        Case("fabricated_quote", _output(question, quote="5000 kg savings guaranteed"), rejected),
        Case("short_quote", _output(question, quote="1000"), rejected),
        Case("empty_citations", json.dumps({
            "questions": [{"question": question, "citations": []}],
        }), rejected),
        Case("narrative_without_json", "This proves substantial financial savings.", rejected),
        Case("extra_approval_property", _output(question, implementation_permitted=True), rejected),
        Case("empty_questions", '{"questions":[]}', rejected),
        Case("statement_not_question", _output("A stock cutoff caused the discrepancy."), rejected),
        Case("excessive_question_length", _output("Could " + "a" * 250 + "?"), rejected),
        Case("incorrect_json_schema", '{"findings":[{"key":"S1"}]}', rejected),
        Case("arabic_question_mark_gap", _output("هل يؤثر توقيت الجرد على الفرق؟"), rejected),
    )
    results = []
    for case in cases:
        answer = validate_grounded_questions(case.output, source)
        actual = answer["status"]
        results.append({
            "case": case.key, "expected": case.expected_status,
            "actual": actual, "passed": actual == case.expected_status,
        })
    return {
        "benchmark": "stage8_synthetic_citation_validation_v1",
        "total": len(results),
        "passed": sum(result["passed"] for result in results),
        "results": results,
        "model_calls": 0,
        "real_documents_used": False,
        "measures_semantic_faithfulness": False,
        "measures_model_accuracy": False,
        "measures_pii_detection": False,
        "known_gap": (
            "Exact quotes can accompany misleading interpretations; human "
            "review remains necessary. Arabic question mark support is "
            "not yet accepted by the Stage 6 parser."
        ),
        "safe_to_use_with_customers": False,
    }


def main() -> int:
    result = synthetic_pilot_benchmark()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["passed"] == result["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
