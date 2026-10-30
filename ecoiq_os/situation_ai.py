"""Optional reviewed-evidence AI research questions for a situation.

The actual model is only contacted through Stage 6's triple-gated service.
This module never asks an LLM to interpret verses or issue religious rulings,
and never trusts a client-provided project, reviewer or 'approved' attribute.
No public HTTP route uses this service.
"""
from __future__ import annotations

from api.models import ProcessAnalysisRun
from ecoiq_os.decision_islah import build_preliminary_brief
from ecoiq_os.grounded_ai import prepare_grounded_draft
from ecoiq_os.situation_guidance import assemble_situation_guidance
from gold_intelligence import access


def prepare_research_situation(
    *, project, user, run: ProcessAnalysisRun,
    external_transfer_approved: bool = False,
    gateway=None,
) -> dict[str, object]:
    """Internal caller provides authenticated actor and project server-side.

    Possible statuses: ACCESS_DENIED, INVALID_REPORTED_ANALYSIS, and
    Stage 6's NO_REVIEWED_SOURCES / EXTERNAL_MODEL_DISABLED /
    MODEL_OUTPUT_REJECTED / REVIEW_REQUIRED. Unapproved data never sent.
    """
    if not access.can(user, project, access.ANALYSE) or run.project_id != project.pk:
        return {"status": "ACCESS_DENIED", "model_called": False}
    try:
        kpi = run.summary["kpi"]
        brief = build_preliminary_brief(
            case_id=run.case_id, domain=run.domain,
            process_name=run.process_name, resource_type=run.resource_type,
            period=run.period, unit=run.unit,
            reported_input=kpi["denominator"], reported_loss=kpi["numerator"],
        )
        guidance = assemble_situation_guidance(brief)
    except (KeyError, ValueError, TypeError):
        return {"status": "INVALID_REPORTED_ANALYSIS", "model_called": False}

    draft = prepare_grounded_draft(
        project=project, user=user, run=run,
        external_transfer_approved=external_transfer_approved, gateway=gateway,
    )
    if draft.get("status") != "REVIEW_REQUIRED":
        return {
            "status": draft.get("status", "MODEL_OUTPUT_REJECTED"),
            "model_called": draft.get("model_called", False),
            "situation_guidance": guidance,
            "ai_questions": [],
            "implementation_permitted": False,
            "shariah_verdict": None,
        }
    # Stage 6 accepted exact-source citation matching, not factual validity.
    # Keep questions UNTESTED until independent Stage 7 human review.
    return {
        "status": "REVIEW_REQUIRED",
        "model_called": True,
        "situation_guidance": guidance,
        "ai_questions": draft["questions"],
        "source_manifest": draft["source_manifest"],
        "approval_recorded": False,
        "implementation_permitted": False,
        "shariah_verdict": None,
        "religious_research_status": "SCHOLAR_REVIEW_REQUIRED",
    }
