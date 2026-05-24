"""
EcoIQ — AI Integration Architecture (Phase 4 Stubs)

This module defines the interfaces for future AI-powered features.
All classes raise NotImplementedError — implement in Phase 4 using
the Anthropic Claude API (key already wired via ANTHROPIC_API_KEY).

Design principles:
  - Each feature is a standalone class with a clear interface
  - Inputs and outputs are plain Python dicts/lists (no ORM coupling)
  - Methods are synchronous and idempotent where possible
  - All return values include a `confidence` score (0.0–1.0)
  - Errors are raised as specific exceptions, never silently swallowed

Roadmap:
  Phase 4a — PDFExtractor         (AI reads audit PDFs → structured KPIs)
  Phase 4b — RecommendationEngine (AI suggests improvements per company)
  Phase 4c — AnomalyDetector      (AI flags sudden score changes / inconsistencies)
  Phase 4d — NarrativeGenerator   (AI drafts company profile intro text)
  Phase 4e — RiskScorer           (AI produces forward-looking environmental risk score)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ── Shared types ───────────────────────────────────────────────────────────────

@dataclass
class PillarScores:
    """Structured pillar scores extracted or computed by AI."""
    pollution_footprint: int    # 0–100
    reduction_progress: int     # 0–100
    investment: int             # 0–100
    transparency: int           # 0–100
    community_impact: int       # 0–100
    confidence: float           # 0.0–1.0
    raw_evidence: dict = field(default_factory=dict)


@dataclass
class RecommendationItem:
    title:            str
    priority:         str          # 'high' | 'medium' | 'low'
    description:      str
    investment_range: Optional[str]
    expected_impact:  Optional[str]
    timeline:         Optional[str]
    confidence:       float


@dataclass
class AnomalyReport:
    company_slug: str
    anomalies:    list[dict]  # [{'field': ..., 'reason': ..., 'severity': ...}]
    clean:        bool         # True if no anomalies found


# ── AI feature stubs ───────────────────────────────────────────────────────────

class PDFExtractor:
    """
    Phase 4a: Extract structured KPI data from PDF audit reports.

    Will use Anthropic Claude with vision/document capabilities to:
      1. Read uploaded PDF (already stored in Wagtail Documents)
      2. Identify emission figures, investment amounts, project data
      3. Map raw text to pillar scores with calibrated confidence
      4. Return structured PillarScores ready for admin review

    Integration point:
      Call from league/admin.py Evidence verification workflow.
      Store extracted scores in a draft ScoreHistory record for admin approval.
    """

    def extract_kpis(self, pdf_path: str, company_slug: str) -> PillarScores:
        """
        Args:
            pdf_path:     Local filesystem path to the PDF.
            company_slug: Company slug for context (helps calibrate against history).

        Returns:
            PillarScores with confidence score.
            confidence < 0.6 → show warning in admin, require manual review.
            confidence ≥ 0.8 → can auto-populate draft scores.
        """
        raise NotImplementedError(
            "Phase 4a: implement with "
            "anthropic.Anthropic().messages.create(model='claude-opus-4-5', ...)"
        )

    def extract_metrics(self, pdf_path: str) -> dict:
        """
        Lower-level: extract raw numeric metrics without normalisation.
        Returns: {
            'co2_tonnes': ...,
            'investment_usd': ...,
            'pm25_kg': ...,
            'households_helped': ...,
            'methodology_notes': ...,
        }
        """
        raise NotImplementedError("Phase 4a")


class RecommendationEngine:
    """
    Phase 4b: Generate AI improvement recommendations for a company.

    Will use Claude to:
      1. Read company's current scores, projects, and evidence
      2. Compare against sector peers (from league.Company queryset)
      3. Identify the highest-leverage improvement areas
      4. Draft specific, actionable recommendations with investment estimates

    Integration point:
      Add a "Generate AI Recommendations" button in CompanyAdmin.
      Store results as RecommendationBlock entries in an AdminDraft model
      (pending human review before publishing to CompanyPage StreamField).
    """

    def generate(
        self,
        company_slug: str,
        max_recommendations: int = 5,
    ) -> list[RecommendationItem]:
        """
        Args:
            company_slug:         Target company.
            max_recommendations:  Cap on number of items returned.

        Returns:
            List of RecommendationItem sorted by priority then confidence.
        """
        raise NotImplementedError(
            "Phase 4b: read company + peers from DB, "
            "call Claude API with structured prompt, parse JSON response"
        )


class AnomalyDetector:
    """
    Phase 4c: Detect reporting inconsistencies and sudden score changes.

    Will use Claude to:
      1. Compare company's score history
      2. Cross-check claimed investments against evidence documents
      3. Flag implausible YoY improvement rates
      4. Detect greenwashing patterns (high transparency score, low actual data)

    Integration point:
      Run nightly via a management command (cron / Render scheduled job).
      Store AnomalyReport in a new AnomalyLog model for admin review.
      Send email to LEAD_NOTIFY_EMAIL if high-severity anomaly found.
    """

    def detect(self, company_slug: str) -> AnomalyReport:
        raise NotImplementedError("Phase 4c")

    def detect_all(self) -> list[AnomalyReport]:
        """Run anomaly detection for every company. Use in nightly batch."""
        raise NotImplementedError("Phase 4c")


class NarrativeGenerator:
    """
    Phase 4d: Draft editorial narrative for CompanyPage hero intro and body.

    Will use Claude to:
      1. Read company KPIs, projects, and evidence
      2. Write a factual, Bloomberg-style company profile paragraph
      3. Output structured text ready for Wagtail RichTextField

    Integration point:
      "Generate draft narrative" action in Wagtail admin CompanyPage editor.
      Draft stored in page body as a RichTextSectionBlock awaiting editor approval.
    """

    def generate_intro(self, company_slug: str) -> str:
        """Returns HTML-safe rich text paragraph (max ~200 words)."""
        raise NotImplementedError("Phase 4d")

    def generate_project_summary(self, project_id: int) -> str:
        """Returns 2–3 sentence project description from KPI data."""
        raise NotImplementedError("Phase 4d")


class RiskScorer:
    """
    Phase 4e: Forward-looking environmental risk assessment.

    Produces a risk score (0–100) representing the probability of:
      - regulatory penalty in next 12 months
      - public reputational event
      - environmental incident based on operational data

    Integration point:
      Add risk_score field to league.Company.
      Display as a separate 'Risk Outlook' widget on CompanyPage.
    """

    def score(self, company_slug: str) -> dict:
        """
        Returns: {
            'risk_score': int (0-100, higher = more risk),
            'drivers': [{'factor': ..., 'weight': ...}],
            'outlook_label': str,
            'confidence': float,
        }
        """
        raise NotImplementedError("Phase 4e")


# ── Registry ───────────────────────────────────────────────────────────────────

AI_FEATURES = {
    'pdf_extraction':        PDFExtractor,
    'recommendations':       RecommendationEngine,
    'anomaly_detection':     AnomalyDetector,
    'narrative_generation':  NarrativeGenerator,
    'risk_scoring':          RiskScorer,
}
"""
Registry of all planned AI features.
Check each class's docstring for integration points.
Phase 4 implementation order: 4a → 4b → 4c → 4d → 4e
"""
