"""
EcoIQ Intelligence OS — Compute Engine.

Functions for aggregating, alerting, and generating intelligence insights.
All functions are safe to call from management commands or web requests.
"""
import hashlib
import json
import logging
from collections import defaultdict
from decimal import Decimal
from datetime import date, timedelta

log = logging.getLogger('intelligence.compute')


# ── Country Intelligence ───────────────────────────────────────────────────────

def compute_country_intelligence():
    """
    Aggregate all Company records by country → create/update CountryIntelligence.
    Returns list of updated CountryIntelligence objects.
    """
    from league.models import Company
    from intelligence.models import CountryIntelligence

    # Group companies by country
    by_country = defaultdict(list)
    for co in Company.objects.prefetch_related('projects').all():
        by_country[co.country].append(co)

    updated = []
    for country_name, companies in by_country.items():
        if not country_name:
            continue

        n = len(companies)
        avg = lambda attr: round(sum(float(getattr(c, attr)) for c in companies) / n, 1)

        national_score = Decimal(str(round(
            sum(float(c.ecoiq_score) for c in companies) / n, 1
        )))

        total_co2 = sum(c.total_co2_reduced for c in companies)
        total_inv = sum(c.total_investment_usd for c in companies)
        total_hh  = sum(c.total_households_helped for c in companies)
        total_proj= sum(c.projects.count() for c in companies)

        # Sector distribution
        sector_dist = defaultdict(int)
        for co in companies:
            sector_dist[co.sector] += 1
        top_sector = max(sector_dist, key=sector_dist.get) if sector_dist else ''

        # Reporting percentage (has at least one evidence)
        from league.models import Evidence
        reporting = sum(
            1 for c in companies
            if Evidence.objects.filter(company=c).exists()
        )
        reporting_pct = round(reporting / n * 100, 1)

        country_code = _to_code(country_name)

        ci, _ = CountryIntelligence.objects.get_or_create(
            country_code=country_code,
            defaults={'country_name': country_name},
        )

        # Trend: compare against 6m ago snapshot
        old_score = ci.national_ecoiq_score if ci.pk else None
        trend_delta = Decimal('0.0')
        trend_dir   = 'stable'
        if old_score is not None:
            trend_delta = national_score - old_score
            if trend_delta >= Decimal('2.0'):
                trend_dir = 'improving'
            elif trend_delta <= Decimal('-2.0'):
                trend_dir = 'declining'

        CountryIntelligence.objects.filter(pk=ci.pk).update(
            country_name             = country_name,
            country_code             = country_code,
            national_ecoiq_score     = national_score,
            company_count            = n,
            verified_company_count   = sum(1 for c in companies if c.verified),
            avg_pollution            = Decimal(str(avg('score_pollution_footprint'))),
            avg_reduction            = Decimal(str(avg('score_reduction_progress'))),
            avg_investment           = Decimal(str(avg('score_investment'))),
            avg_transparency         = Decimal(str(avg('score_transparency'))),
            avg_community            = Decimal(str(avg('score_community_impact'))),
            total_co2_reduction_tonnes= total_co2,
            total_investment_usd     = total_inv,
            total_households_helped  = total_hh,
            total_projects           = total_proj,
            sector_distribution      = dict(sector_dist),
            top_sector               = top_sector,
            reporting_pct            = reporting_pct,
            score_6m_ago             = old_score,
            trend_direction          = trend_dir,
            trend_delta              = trend_delta,
        )
        ci.refresh_from_db()
        updated.append(ci)
        log.info('Country computed: %s → EcoIQ %.1f', country_name, national_score)

    # Assign transparency ranks
    ranked = sorted(updated, key=lambda c: c.reporting_pct, reverse=True)
    for i, ci in enumerate(ranked, 1):
        CountryIntelligence.objects.filter(pk=ci.pk).update(transparency_rank=i)

    return updated


def _to_code(country_name: str) -> str:
    """Slugify country name into a stable lowercase code."""
    from django.utils.text import slugify
    return slugify(country_name)[:30] or 'unknown'


# ── Alert Generation ───────────────────────────────────────────────────────────

def generate_alerts_for_company(company, prev_score: float | None = None):
    """
    Compare current company state against previous snapshot and emit alerts.
    Call this after ingestion pipeline completes or after score recalc.
    """
    from intelligence.models import IntelligenceAlert

    alerts_created = []
    current_score = float(company.ecoiq_score)

    # Score drop alert
    if prev_score is not None:
        delta = current_score - prev_score
        if delta <= -5:
            sev = 'critical' if delta <= -15 else 'high' if delta <= -8 else 'medium'
            a = IntelligenceAlert.objects.create(
                alert_type='score_drop',
                severity=sev,
                company=company,
                title=f'{company.name} — EcoIQ dropped {abs(delta):.1f} points',
                body=(
                    f'EcoIQ score fell from {prev_score:.1f} to {current_score:.1f}. '
                    f'This represents a {"critical" if sev == "critical" else "significant"} '
                    f'environmental performance regression requiring immediate review.'
                ),
                metric_before=Decimal(str(prev_score)),
                metric_after=Decimal(str(current_score)),
                metric_delta=Decimal(str(delta)),
            )
            alerts_created.append(a)

        elif delta >= 8:
            a = IntelligenceAlert.objects.create(
                alert_type='score_surge',
                severity='info',
                company=company,
                title=f'{company.name} — EcoIQ improved +{delta:.1f} points',
                body=f'Score moved from {prev_score:.1f} to {current_score:.1f}.',
                metric_before=Decimal(str(prev_score)),
                metric_after=Decimal(str(current_score)),
                metric_delta=Decimal(str(delta)),
            )
            alerts_created.append(a)

    # Transparency warning
    if company.score_transparency < 25:
        if not IntelligenceAlert.objects.filter(
            company=company, alert_type='transparency_loss',
            created_at__gte=date.today() - timedelta(days=30),
        ).exists():
            IntelligenceAlert.objects.create(
                alert_type='transparency_loss',
                severity='high',
                company=company,
                title=f'{company.name} — Critical transparency gap',
                body=(
                    f'Transparency score is {company.score_transparency}/100. '
                    'No public ESG reports or audits detected in the evidence base.'
                ),
                metric_after=Decimal(str(company.score_transparency)),
            )

    return alerts_created


def generate_alert(alert_type: str, company, severity: str, title: str, body: str = '',
                   before=None, after=None):
    """Convenience wrapper for one-off alert creation."""
    from intelligence.models import IntelligenceAlert
    return IntelligenceAlert.objects.create(
        alert_type=alert_type,
        severity=severity,
        company=company,
        title=title,
        body=body,
        metric_before=Decimal(str(before)) if before is not None else None,
        metric_after=Decimal(str(after)) if after is not None else None,
        metric_delta=Decimal(str(after - before)) if (before is not None and after is not None) else None,
    )


# ── Strategic Signal Generation ────────────────────────────────────────────────

def sync_strategic_signals_from_audit():
    """
    Walk approved AIFinding records and create StrategicSignal entries
    for finding types that map to strategic modules.
    """
    from audit.models import AIFinding
    from intelligence.models import StrategicSignal

    FINDING_TO_MODULE = {
        'methane_metric':  ('methane',      'risk'),
        'co2_metric':      ('coal_transition','neutral'),
        'investment':      ('ethical_investment','positive'),
        'project':         ('modernisation','positive'),
        'coal_replacement':('coal_transition','positive'),
        'water_metric':    ('water_restoration','neutral'),
        'greenwashing':    ('ethical_investment','risk'),
    }

    created = 0
    for finding in AIFinding.objects.filter(status='approved').select_related('job__company'):
        company = finding.job.company
        if not company:
            continue
        mapping = FINDING_TO_MODULE.get(finding.finding_type)
        if not mapping:
            continue
        module, polarity = mapping

        # Deduplicate: one signal per finding per company per module
        if StrategicSignal.objects.filter(
            company=company, module=module,
            title=finding.title[:255],
        ).exists():
            continue

        StrategicSignal.objects.create(
            module=module,
            company=company,
            polarity=polarity,
            title=finding.title[:255],
            description=finding.description[:2000],
            metric_value=finding.numeric_value,
            metric_unit=finding.unit,
            source_url='',
            year=finding.year,
            confidence=finding.confidence_score,
        )
        created += 1

    log.info('Strategic signals synced: %d new', created)
    return created


# ── Content Hash Monitoring ────────────────────────────────────────────────────

def check_monitor_target(watch):
    """
    Fetch a MonitorWatch URL, hash the content, compare.
    Returns True if a change was detected.
    """
    import requests as http_requests
    from intelligence.models import MonitorWatch, IntelligenceAlert
    from django.utils import timezone as tz

    try:
        resp = http_requests.get(
            watch.url,
            headers={'User-Agent': 'EcoIQ-Monitor/1.0 (+https://ecoiq.uk/about)'},
            timeout=15,
        )
        if resp.status_code != 200:
            MonitorWatch.objects.filter(pk=watch.pk).update(
                last_checked_at=tz.now(),
                consecutive_errors=watch.consecutive_errors + 1,
            )
            return False

        content = resp.content[:500_000]  # first 500 KB
        new_hash = hashlib.sha256(content).hexdigest()
        changed  = (new_hash != watch.last_content_hash) and bool(watch.last_content_hash)

        MonitorWatch.objects.filter(pk=watch.pk).update(
            last_checked_at=tz.now(),
            last_content_hash=new_hash,
            last_content_size=len(content),
            change_detected=changed,
            change_detected_at=tz.now() if changed else watch.change_detected_at,
            consecutive_errors=0,
        )

        if changed:
            IntelligenceAlert.objects.create(
                alert_type='monitor_change',
                severity='medium',
                company=watch.company,
                title=f'{watch.company.name} — website content updated',
                body=f'Change detected at {watch.url}. New content may include ESG disclosures.',
                source_url=watch.url,
            )

        return changed

    except Exception as exc:
        log.warning('Monitor check failed for %s: %s', watch.url, exc)
        MonitorWatch.objects.filter(pk=watch.pk).update(
            consecutive_errors=watch.consecutive_errors + 1,
        )
        return False


# ── AI Executive Briefing ──────────────────────────────────────────────────────

def generate_executive_briefing(company):
    """
    Use Claude to generate a concise executive intelligence briefing for a company.
    Stores result in ExecutiveBriefing. Returns the briefing object.
    """
    from django.conf import settings
    from intelligence.models import ExecutiveBriefing
    from league.scoring import get_tier

    tier = get_tier(float(company.ecoiq_score))
    recent_projects = list(company.projects.order_by('-start_date')[:3])
    recent_alerts   = list(company.alerts.order_by('-created_at')[:5])

    context_block = f"""Company: {company.name}
Sector: {company.get_sector_display()}
Country: {company.country}
EcoIQ Score: {company.ecoiq_score} ({tier.label})
Rank: #{company.rank or '—'}

Pillar Scores (0-100):
  Pollution Footprint:  {company.score_pollution_footprint}
  Reduction Progress:   {company.score_reduction_progress}
  Environmental Investment: {company.score_investment}
  Transparency:         {company.score_transparency}
  Community Impact:     {company.score_community_impact}

Recent Projects: {', '.join(p.name for p in recent_projects) or 'None recorded'}
Recent Alerts: {', '.join(a.title[:60] for a in recent_alerts) or 'None'}
Verified: {'Yes' if company.verified else 'No'}
"""

    prompt = f"""You are an institutional ESG analyst writing a briefing for a sovereign wealth fund.

{context_block}

Write a structured executive intelligence briefing in 200-300 words. Format as JSON:
{{
  "headline": "One decisive verdict sentence (max 120 chars)",
  "body": "3-4 paragraph briefing in professional financial/ESG analyst tone",
  "key_risks": ["Risk 1 (max 80 chars)", "Risk 2", "Risk 3"],
  "key_drivers": ["Driver 1 (max 80 chars)", "Driver 2"],
  "action_items": ["Action 1 (max 100 chars)", "Action 2", "Action 3"]
}}

Tone: Bloomberg Intelligence. Concise. Institutional. Evidence-based. No marketing language.
Return JSON only."""

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        model  = getattr(settings, 'ECOIQ_AI_MODEL', 'claude-opus-4-5')

        response = client.messages.create(
            model=model,
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text if response.content else ''

        import re, json as _json
        text = re.sub(r'```(?:json)?\s*', '', text).strip()
        start = text.find('{')
        end   = text.rfind('}')
        data  = _json.loads(text[start:end + 1]) if start != -1 else {}

        briefing = ExecutiveBriefing.objects.create(
            scope='company',
            company=company,
            title=f'Intelligence Brief: {company.name}',
            headline=data.get('headline', '')[:500],
            body=data.get('body', ''),
            key_risks=data.get('key_risks', []),
            key_drivers=data.get('key_drivers', []),
            action_items=data.get('action_items', []),
            model_used=model,
            token_count=response.usage.input_tokens + response.usage.output_tokens,
        )
        return briefing

    except Exception as exc:
        log.error('Briefing generation failed for %s: %s', company.name, exc)
        return None


# ── Rank Movement ─────────────────────────────────────────────────────────────

def get_rank_movers(days: int = 30, limit: int = 10):
    """
    Return companies whose rank changed most (up and down) in the last N days.
    Returns dict: {'gainers': [...], 'losers': [...]}
    """
    from league.models import Company, ScoreHistory

    cutoff = date.today() - timedelta(days=days)
    gainers = []
    losers  = []

    for co in Company.objects.filter(rank__isnull=False):
        old_snap = ScoreHistory.objects.filter(
            company=co, date__lte=cutoff
        ).order_by('-date').first()
        if not old_snap or old_snap.rank is None or co.rank is None:
            continue
        movement = old_snap.rank - co.rank   # positive = improved (rank went down numerically)
        if movement >= 2:
            gainers.append({'company': co, 'movement': movement,
                            'old_rank': old_snap.rank, 'new_rank': co.rank})
        elif movement <= -2:
            losers.append({'company': co, 'movement': movement,
                           'old_rank': old_snap.rank, 'new_rank': co.rank})

    gainers.sort(key=lambda x: x['movement'], reverse=True)
    losers.sort(key=lambda x:  x['movement'])
    return {'gainers': gainers[:limit], 'losers': losers[:limit]}
