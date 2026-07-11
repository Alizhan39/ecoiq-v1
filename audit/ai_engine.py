"""
EcoIQ AI Findings Engine
-------------------------
Analyzes ESG / sustainability / audit PDFs using the Anthropic API.

Public API:
    run_ai_analysis(job: AIAnalysisJob) → None
        Reads job.pdf_file, calls Claude, stores findings in DB.

    apply_approved_findings(job, company) → dict
        Writes approved AIFindings into league Company data.
"""
from __future__ import annotations

import json
import logging
import os
import re
import textwrap
from datetime import date, datetime, timezone

from django.conf import settings
from django.utils import timezone as tz

logger = logging.getLogger(__name__)

# ─── Model imports (lazy to avoid circular imports) ───────────────────────────
def _models():
    from .models import AIAnalysisJob, AIFinding, AIScoreEstimate
    return AIAnalysisJob, AIFinding, AIScoreEstimate


# ─── Anthropic model config ───────────────────────────────────────────────────
AI_MODEL   = getattr(settings, 'ECOIQ_AI_MODEL', 'claude-opus-4-5')
MAX_CHARS  = 90_000   # ~22K tokens — leaves room for system prompt + response
MAX_TOKENS = 8_000    # response budget


# ═══════════════════════════════════════════════════════════════════════════════
# PDF TEXT EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def extract_pdf_text(file_field) -> tuple[str, int]:
    """
    Extract plain text from a Django FileField pointing to a PDF.
    Returns (full_text, page_count).
    Truncates to MAX_CHARS if necessary.
    """
    from pypdf import PdfReader

    file_field.seek(0)
    reader = PdfReader(file_field)
    page_count = len(reader.pages)

    chunks = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ''
        text = text.strip()
        if text:
            chunks.append(f"[PAGE {i + 1}]\n{text}")

    full_text = '\n\n'.join(chunks)

    if len(full_text) > MAX_CHARS:
        full_text = full_text[:MAX_CHARS] + '\n\n[...document truncated at 90,000 characters...]'

    return full_text, page_count


# ═══════════════════════════════════════════════════════════════════════════════
# EXTRACTION PROMPT
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = textwrap.dedent("""
You are an expert environmental intelligence analyst specializing in ESG analysis,
GHG accounting, and environmental compliance for industrial companies in Kazakhstan
and Central Asia. You extract structured environmental data from corporate documents
with precision and intellectual honesty.

Key principles:
- Only extract information EXPLICITLY stated in the document.
- Use confidence scores honestly: 0.9+ for explicit numerical data, 0.5–0.7 for
  inferred/estimated values, 0.3–0.5 for indirect references.
- Flag greenwashing signals: vague commitments without targets, unverified claims,
  missing baseline data, cherry-picked metrics, pledges without action plans.
- For monetary amounts in KZT: 1 USD ≈ 450 KZT (2023 rate). Convert to USD.
- Quote the EXACT source text for each finding — this is critical for analyst review.
- Return ONLY a valid JSON object — no markdown, no preamble, no trailing text.
""").strip()

USER_PROMPT_TEMPLATE = textwrap.dedent("""
Analyze the following document and extract all environmental findings.

DOCUMENT:
{document_text}

Return a single JSON object matching this EXACT schema (all fields required):

{{
  "company_name": "string or null",
  "document_type": "annual_report | sustainability_report | audit_report | government_report | engineering_audit | other",
  "report_year": <integer or null>,

  "pollution_metrics": [
    {{
      "metric_type": "co2 | methane | pm25 | so2 | nox | water | waste | other",
      "value": <number or null>,
      "unit": "string (e.g. tCO2e, kg, m3)",
      "year": <integer or null>,
      "context": "EXACT verbatim quote from document",
      "source_location": "Page X / Section Y",
      "confidence": <0.0–1.0>
    }}
  ],

  "investments": [
    {{
      "description": "string",
      "amount_usd": <number or null>,
      "currency_original": "USD | KZT | EUR | RUB | other",
      "amount_original": <number or null>,
      "project_name": "string or null",
      "year": <integer or null>,
      "context": "EXACT verbatim quote",
      "source_location": "string",
      "confidence": <0.0–1.0>
    }}
  ],

  "projects": [
    {{
      "name": "string",
      "type": "coal_stove | gasification | power_modern | renewable | water_cleanup | waste | tree_planting | filters | methane | other",
      "status": "planned | active | completed",
      "co2_reduction_tonnes": <number or null>,
      "investment_usd": <number or null>,
      "households_helped": <integer or null>,
      "pm25_reduction_kg": <number or null>,
      "location": "string or null",
      "start_year": <integer or null>,
      "completion_year": <integer or null>,
      "context": "EXACT verbatim quote",
      "source_location": "string",
      "confidence": <0.0–1.0>
    }}
  ],

  "greenwashing_signals": [
    {{
      "signal_type": "vague_claim | missing_data | inconsistency | unverified_claim | misleading_comparison | cherry_picking | no_targets | pledge_without_action | inflated_metrics",
      "description": "string — specific critique",
      "severity": "low | medium | high | critical",
      "context": "EXACT verbatim quote or specific claim",
      "source_location": "string",
      "confidence": <0.0–1.0>
    }}
  ],

  "transparency_indicators": [
    {{
      "indicator": "gri_compliance | tcfd_alignment | cdp_filing | third_party_audit | emissions_verification | public_data | iso14001 | sbti_commitment | other",
      "present": true/false,
      "quality": "high | medium | low | absent",
      "notes": "string",
      "context": "EXACT verbatim quote or null",
      "confidence": <0.0–1.0>
    }}
  ],

  "recommendations": [
    {{
      "priority": "critical | high | medium | low",
      "category": "emissions | investment | transparency | community | reporting | methane | coal_transition",
      "title": "string",
      "rationale": "string",
      "estimated_impact": "string",
      "sdgs": [<list of integer SDG numbers>]
    }}
  ],

  "score_estimates": {{
    "pollution_footprint": <0–100>,
    "reduction_progress": <0–100>,
    "investment": <0–100>,
    "transparency": <0–100>,
    "community_impact": <0–100>,
    "ecoiq_composite": <0.0–100.0>,
    "confidence": <0.0–1.0>,
    "reasoning": "detailed explanation — one sentence per pillar",
    "data_gaps": ["list of critical missing data items"]
  }},

  "greenwashing_risk": {{
    "level": "low | medium | high | critical",
    "score": <0–100>,
    "key_signals": ["list of 3–5 main concerns"],
    "verdict": "2–3 sentence assessment paragraph"
  }},

  "executive_summary": "2–3 paragraph summary of key environmental findings",
  "data_quality_notes": "1 paragraph assessment of document quality, completeness, and reliability"
}}
""").strip()


# ═══════════════════════════════════════════════════════════════════════════════
# JSON PARSER  (handles markdown code fences that LLMs sometimes emit)
# ═══════════════════════════════════════════════════════════════════════════════

def _parse_json(text: str) -> dict:
    """Extract and parse JSON from an LLM response (may be wrapped in ```json ... ```)."""
    text = text.strip()

    # Strip markdown code fences
    match = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', text)
    if match:
        text = match.group(1).strip()

    # Find first { ... last }
    start = text.find('{')
    end   = text.rfind('}')
    if start != -1 and end != -1:
        text = text[start:end + 1]

    return json.loads(text)


# ═══════════════════════════════════════════════════════════════════════════════
# FINDING FACTORIES  (convert AI JSON → AIFinding / AIScoreEstimate records)
# ═══════════════════════════════════════════════════════════════════════════════

def _clamp(v, lo=0, hi=100):
    if v is None: return None
    return max(lo, min(hi, int(v)))


def _clamp_f(v, lo=0.0, hi=1.0):
    if v is None: return lo
    return max(lo, min(hi, float(v)))


def _save_pollution_metrics(job, metrics: list):
    _, AIFinding, _ = _models()
    TYPE_MAP = {
        'co2': 'co2_metric', 'methane': 'methane_metric',
        'pm25': 'pm25_metric', 'so2': 'so2_metric',
        'nox': 'nox_metric', 'water': 'water_metric',
        'waste': 'waste_metric', 'other': 'pollution_other',
    }
    for m in metrics or []:
        ftype = TYPE_MAP.get((m.get('metric_type') or 'other').lower(), 'pollution_other')
        val   = m.get('value')
        unit  = (m.get('unit') or '').strip()
        year  = m.get('year')

        title = f"{m.get('metric_type', 'Pollutant').upper()} emission"
        if val is not None:
            title += f": {val:,.2f} {unit}"
        if year:
            title += f" ({year})"

        AIFinding.objects.create(
            job=job,
            finding_type=ftype,
            title=title[:255],
            description=m.get('context') or '',
            numeric_value=val,
            unit=unit,
            year=year,
            source_quote=(m.get('context') or '')[:2000],
            source_location=(m.get('source_location') or '')[:200],
            confidence_score=_clamp_f(m.get('confidence', 0.5)),
            extra_data={'metric_type': m.get('metric_type')},
        )


def _save_investments(job, investments: list):
    _, AIFinding, _ = _models()
    for inv in investments or []:
        amount = inv.get('amount_usd') or 0
        title  = inv.get('description') or 'Environmental investment'
        if amount:
            title = f"${amount:,.0f} — {title}"

        AIFinding.objects.create(
            job=job,
            finding_type='investment',
            title=title[:255],
            description=inv.get('description') or '',
            numeric_value=amount or None,
            unit='USD',
            year=inv.get('year'),
            source_quote=(inv.get('context') or '')[:2000],
            source_location=(inv.get('source_location') or '')[:200],
            confidence_score=_clamp_f(inv.get('confidence', 0.5)),
            extra_data={
                'project_name':      inv.get('project_name'),
                'currency_original': inv.get('currency_original'),
                'amount_original':   inv.get('amount_original'),
            },
        )


def _save_projects(job, projects: list):
    _, AIFinding, _ = _models()
    for proj in projects or []:
        ptype = proj.get('type') or 'other'
        if ptype == 'coal_replacement':
            ptype = 'coal_replacement'

        co2 = proj.get('co2_reduction_tonnes')
        inv = proj.get('investment_usd')
        title = proj.get('name') or 'Environmental project'

        AIFinding.objects.create(
            job=job,
            finding_type='project' if ptype != 'coal_replacement' else 'coal_replacement',
            title=title[:255],
            description=proj.get('context') or '',
            numeric_value=co2,
            unit='tCO2e/yr' if co2 else '',
            year=proj.get('start_year'),
            source_quote=(proj.get('context') or '')[:2000],
            source_location=(proj.get('source_location') or '')[:200],
            confidence_score=_clamp_f(proj.get('confidence', 0.5)),
            extra_data={
                'project_type':          ptype,
                'status':                proj.get('status'),
                'investment_usd':        inv,
                'households_helped':     proj.get('households_helped'),
                'pm25_reduction_kg':     proj.get('pm25_reduction_kg'),
                'location':              proj.get('location'),
                'start_year':            proj.get('start_year'),
                'completion_year':       proj.get('completion_year'),
            },
        )


def _save_greenwashing(job, signals: list):
    _, AIFinding, _ = _models()
    for sig in signals or []:
        sev  = sig.get('severity') or 'medium'
        stype= sig.get('signal_type') or 'other'
        desc = sig.get('description') or ''

        title = f"[{sev.upper()}] {stype.replace('_', ' ').title()}: {desc}"[:255]

        AIFinding.objects.create(
            job=job,
            finding_type='greenwashing',
            title=title,
            description=desc,
            source_quote=(sig.get('context') or '')[:2000],
            source_location=(sig.get('source_location') or '')[:200],
            confidence_score=_clamp_f(sig.get('confidence', 0.6)),
            extra_data={
                'signal_type': stype,
                'severity':    sev,
            },
        )


def _save_transparency(job, indicators: list):
    _, AIFinding, _ = _models()
    for ind in indicators or []:
        present = ind.get('present', False)
        quality = ind.get('quality') or 'absent'
        indicator = ind.get('indicator') or 'other'
        notes     = ind.get('notes') or ''

        title = f"{'✓' if present else '✗'} {indicator.replace('_', ' ').upper()}"
        if quality and quality != 'absent':
            title += f" — {quality} quality"

        AIFinding.objects.create(
            job=job,
            finding_type='transparency',
            title=title[:255],
            description=notes,
            source_quote=(ind.get('context') or '')[:2000],
            confidence_score=_clamp_f(ind.get('confidence', 0.6)),
            extra_data={
                'indicator': indicator,
                'present':   present,
                'quality':   quality,
            },
        )


def _save_recommendations(job, recs: list):
    _, AIFinding, _ = _models()
    PRIORITY_ORDER = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    for rec in recs or []:
        title    = rec.get('title') or 'Recommendation'
        priority = rec.get('priority') or 'medium'
        rationale= rec.get('rationale') or ''
        impact   = rec.get('estimated_impact') or ''

        AIFinding.objects.create(
            job=job,
            finding_type='recommendation',
            title=f"[{priority.upper()}] {title}"[:255],
            description=f"{rationale}\n\nEstimated impact: {impact}".strip(),
            confidence_score=0.8,
            extra_data={
                'priority':         priority,
                'category':         rec.get('category'),
                'estimated_impact': impact,
                'sdgs':             rec.get('sdgs') or [],
            },
        )


def _save_score_estimate(job, score_data: dict, gw_data: dict):
    _, _, AIScoreEstimate = _models()
    se = score_data or {}
    gw = gw_data   or {}

    AIScoreEstimate.objects.update_or_create(
        job=job,
        defaults={
            'est_pollution':    _clamp(se.get('pollution_footprint')),
            'est_reduction':    _clamp(se.get('reduction_progress')),
            'est_investment':   _clamp(se.get('investment')),
            'est_transparency': _clamp(se.get('transparency')),
            'est_community':    _clamp(se.get('community_impact')),
            'est_ecoiq':        round(float(se.get('ecoiq_composite') or 0), 1),
            'confidence':       _clamp_f(se.get('confidence', 0.5)),
            'reasoning':        se.get('reasoning') or '',
            'data_gaps':        se.get('data_gaps') or [],
            'greenwashing_level':   gw.get('level') or '',
            'greenwashing_score':   _clamp(gw.get('score')),
            'greenwashing_signals': gw.get('key_signals') or [],
            'greenwashing_verdict': gw.get('verdict') or '',
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ANALYSIS RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

def run_ai_analysis(job) -> None:
    """
    Run the full AI analysis pipeline on job.pdf_file.
    Updates job fields and creates AIFinding / AIScoreEstimate records.
    Raises on fatal errors (caller should set job.status = 'failed').
    """
    import anthropic

    AIAnalysisJob, _, _ = _models()

    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY is not set. "
            "Add it to your .env file (local) or Render dashboard (production)."
        )

    # Mark as processing
    job.status     = 'processing'
    job.started_at = tz.now()
    job.save(update_fields=['status', 'started_at'])

    try:
        # ── 1. Extract PDF text ───────────────────────────────────────────────
        job.pdf_file.open('rb')
        doc_text, page_count = extract_pdf_text(job.pdf_file)
        job.pdf_file.close()

        if not doc_text.strip():
            raise ValueError(
                "No text could be extracted from this PDF. "
                "The file may be image-only or password-protected."
            )

        job.pages_analyzed = page_count
        job.chars_analyzed = len(doc_text)
        job.save(update_fields=['pages_analyzed', 'chars_analyzed'])

        # ── 2. Call Anthropic API ─────────────────────────────────────────────
        client   = anthropic.Anthropic(api_key=api_key)
        user_msg = USER_PROMPT_TEMPLATE.format(document_text=doc_text)

        response = client.messages.create(
            model=AI_MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': user_msg}],
        )

        raw_text = response.content[0].text
        job.model_used    = AI_MODEL
        job.input_tokens  = response.usage.input_tokens
        job.output_tokens = response.usage.output_tokens
        job.save(update_fields=['model_used', 'input_tokens', 'output_tokens'])

        # ── 3. Parse JSON ─────────────────────────────────────────────────────
        try:
            data = _parse_json(raw_text)
        except json.JSONDecodeError as exc:
            logger.error("JSON parse error for job %s: %s\n\nRaw:\n%s", job.pk, exc, raw_text[:1000])
            raise ValueError(f"AI returned malformed JSON: {exc}")

        job.raw_response = data
        job.save(update_fields=['raw_response'])

        # ── 4. Persist top-level metadata ─────────────────────────────────────
        job.detected_company_name = (data.get('company_name') or '')[:255]
        job.detected_doc_type     = (data.get('document_type') or '')[:50]
        job.detected_year         = data.get('report_year')
        job.executive_summary     = data.get('executive_summary') or ''
        job.data_quality_notes    = data.get('data_quality_notes') or ''
        job.save(update_fields=[
            'detected_company_name', 'detected_doc_type', 'detected_year',
            'executive_summary', 'data_quality_notes',
        ])

        # ── 5. Delete any stale findings from a previous run ──────────────────
        job.findings.all().delete()
        if hasattr(job, 'score_estimate'):
            job.score_estimate.delete()

        # ── 6. Persist findings ───────────────────────────────────────────────
        _save_pollution_metrics(job, data.get('pollution_metrics', []))
        _save_investments(job,       data.get('investments', []))
        _save_projects(job,          data.get('projects', []))
        _save_greenwashing(job,      data.get('greenwashing_signals', []))
        _save_transparency(job,      data.get('transparency_indicators', []))
        _save_recommendations(job,   data.get('recommendations', []))
        _save_score_estimate(job,    data.get('score_estimates', {}),
                                     data.get('greenwashing_risk', {}))

        # ── 7. Mark complete ──────────────────────────────────────────────────
        job.status       = 'completed'
        job.completed_at = tz.now()
        job.save(update_fields=['status', 'completed_at'])

        logger.info(
            "AI analysis complete for job %s: %d findings, %d+%d tokens",
            job.pk, job.findings.count(),
            job.input_tokens, job.output_tokens,
        )

    except Exception:
        job.status = 'failed'
        job.save(update_fields=['status'])
        raise


# ═══════════════════════════════════════════════════════════════════════════════
# APPLY APPROVED FINDINGS → LEAGUE COMPANY DATA
# ═══════════════════════════════════════════════════════════════════════════════

def apply_approved_findings(job, company) -> dict:
    """
    Promote approved AI findings into the league Company record.

    Actions performed:
    - Create EnvironmentalProject for each approved project finding
    - Create Evidence record for the analyzed document itself
    - Apply approved AIScoreEstimate to company's pillar scores (optional)
    - Mark applied findings as status='applied'

    Returns a summary dict.
    """
    from audit.models import AIScoreEstimate
    from league.models import EnvironmentalProject, Evidence, ScoreHistory
    from league.scoring import rerank_all

    summary = {
        'projects_created': 0,
        'evidence_created': 0,
        'score_applied':    False,
        'errors':           [],
    }

    approved = job.findings.filter(status='approved')

    # ── 1. Projects ───────────────────────────────────────────────────────────
    for finding in approved.filter(finding_type__in=['project', 'coal_replacement']):
        try:
            ex = finding.extra_data or {}
            start_date = None
            if ex.get('start_year'):
                try:
                    start_date = date(int(ex['start_year']), 1, 1)
                except (ValueError, TypeError):
                    pass

            comp_date = None
            if ex.get('completion_year'):
                try:
                    comp_date = date(int(ex['completion_year']), 12, 31)
                except (ValueError, TypeError):
                    pass

            EnvironmentalProject.objects.create(
                company=company,
                name=finding.title[:255],
                project_type=ex.get('project_type') or 'other',
                status=ex.get('status') or 'active',
                start_date=start_date,
                completion_date=comp_date,
                investment_usd=int(ex['investment_usd']) if ex.get('investment_usd') else None,
                co2_reduction_tonnes=int(finding.numeric_value) if finding.numeric_value else None,
                pm25_reduction_kg=int(ex['pm25_reduction_kg']) if ex.get('pm25_reduction_kg') else None,
                households_helped=int(ex['households_helped']) if ex.get('households_helped') else None,
                location=(ex.get('location') or '')[:255],
                description=finding.description[:2000],
                verified=False,
            )
            finding.status = 'applied'
            finding.save(update_fields=['status'])
            summary['projects_created'] += 1

        except Exception as exc:
            summary['errors'].append(f"Project '{finding.title[:40]}': {exc}")

    # ── 2. Evidence — one record per job document ─────────────────────────────
    try:
        evidence = Evidence.objects.create(
            company=company,
            doc_type='audit_report',
            title=f"AI Analysis: {job.original_filename}",
            url='',
            date_issued=job.completed_at.date() if job.completed_at else date.today(),
            issuer=f"EcoIQ AI Engine ({job.model_used})",
            verification_status='pending',
            notes=(
                f"Automatically extracted by EcoIQ AI Findings Engine.\n"
                f"Job ID: {job.pk} | Pages: {job.pages_analyzed} | "
                f"Tokens: {job.input_tokens + job.output_tokens}\n\n"
                f"{job.executive_summary[:500]}"
            ),
        )
        from evidence_memory.services.memory import create_memory_from_league_evidence
        create_memory_from_league_evidence(evidence)
        summary['evidence_created'] = 1
    except Exception as exc:
        summary['errors'].append(f"Evidence creation: {exc}")

    # ── 3. Score estimate ─────────────────────────────────────────────────────
    try:
        se = job.score_estimate
        if se.approved and not se.applied_at:
            # Patch pillar scores only if estimate is better than placeholder (score > 0)
            fields_changed = []
            if se.est_pollution    is not None:
                company.score_pollution_footprint = se.est_pollution
                fields_changed.append('score_pollution_footprint')
            if se.est_reduction    is not None:
                company.score_reduction_progress  = se.est_reduction
                fields_changed.append('score_reduction_progress')
            if se.est_investment   is not None:
                company.score_investment           = se.est_investment
                fields_changed.append('score_investment')
            if se.est_transparency is not None:
                company.score_transparency         = se.est_transparency
                fields_changed.append('score_transparency')
            if se.est_community    is not None:
                company.score_community_impact     = se.est_community
                fields_changed.append('score_community_impact')

            if fields_changed:
                company.save()   # triggers score recompute in Company.save()
                rerank_all()

                # Snapshot in history
                ScoreHistory.objects.update_or_create(
                    company=company,
                    date=date.today(),
                    defaults={
                        'ecoiq_score':               company.ecoiq_score,
                        'score_pollution_footprint': company.score_pollution_footprint,
                        'score_reduction_progress':  company.score_reduction_progress,
                        'score_investment':           company.score_investment,
                        'score_transparency':         company.score_transparency,
                        'score_community_impact':     company.score_community_impact,
                    },
                )

            se.applied_at = tz.now()
            se.save(update_fields=['applied_at'])
            summary['score_applied'] = True

    except AIScoreEstimate.DoesNotExist:
        pass
    except Exception as exc:
        summary['errors'].append(f"Score application: {exc}")

    # Mark remaining approved findings (investments, transparency) as applied
    approved.filter(status='approved').update(status='applied')

    return summary


# ── re-export for convenience ─────────────────────────────────────────────────
__all__ = ['run_ai_analysis', 'apply_approved_findings', 'extract_pdf_text']
