"""
API v2 serializers — truthful evidence semantics.

v2 exists because v1 publishes a number for every company regardless of whether
anything behind it is evidenced, and a numeric field has no way to say "we do not
know". v2 says it explicitly:

    {"ecoiq_score": null, "score_status": "INSUFFICIENT_EVIDENCE",
     "evidence_coverage": 0, "rank": null}

Three rules the whole contract rests on:

1.  Unknown is null. Never 0, 50, -1, "" or "N/A". A consumer that renders null
    as a blank is telling the truth; one that renders 0 is not, which is exactly
    the failure the current Flutter parser has (`?? 0`).

2.  Status carries the meaning, not the numeral. A genuine measured 0.0 stays
    0.0 and a genuine measured 50.0 stays 50.0, both with
    score_status=PUBLISHED. Nothing about this contract lets a real value be
    mistaken for a missing one, or the reverse.

3.  No second framework. The vocabulary is companies.evidence's, which is in
    turn decision_studio's. This module classifies nothing itself; it asks
    public_score_state() and reports the answer.

v2 is additive. It shares models with v1 and adds no scoring path of its own.
"""
from rest_framework import serializers

from companies.evidence import (
    public_score_state, public_score_state_for_company,
)


class _EvidenceScoreMixin:
    """Shared score/status/coverage triple. Always emitted together."""

    def _state(self, obj):
        raise NotImplementedError

    def get_ecoiq_score(self, obj):
        """The score, or null. Never a stand-in value."""
        state = self._state(obj)
        return round(state.score, 1) if state.available and state.score is not None else None

    def get_score_status(self, obj):
        return self._state(obj).status

    def get_evidence_coverage(self, obj):
        """Whole percent of material inputs with real evidence provenance."""
        return self._state(obj).coverage_percent


class CompanyV2Serializer(_EvidenceScoreMixin, serializers.Serializer):
    """One company in a v2 list or detail response."""

    slug = serializers.CharField()
    name = serializers.CharField()
    sector = serializers.CharField()
    country = serializers.CharField()
    is_public = serializers.BooleanField()
    verified = serializers.BooleanField()

    ecoiq_score = serializers.SerializerMethodField()
    score_status = serializers.SerializerMethodField()
    evidence_coverage = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    def _state(self, obj):
        # Cached per instance: a list response would otherwise recompute coverage
        # once per field, three times per row.
        cached = getattr(obj, '_v2_score_state', None)
        if cached is None:
            cached = public_score_state_for_company(obj)
            obj._v2_score_state = cached
        return cached

    def get_rank(self, obj):
        """
        Null when the score is not publishable.

        A rank is a comparative claim. Publishing one for a company whose score
        cannot be published would assert exactly what the score is withholding.
        """
        return obj.rank if self._state(obj).available else None

    def get_url(self, obj) -> str:
        request = self.context.get('request')
        path = f'/api/v2/companies/{obj.slug}/'
        return request.build_absolute_uri(path) if request else path


class CompanyProfileV2Serializer(_EvidenceScoreMixin, serializers.Serializer):
    """
    Detail response for one company profile.

    The gate is on SCORES, not on facts about the company.

    v1's detail endpoint returns seventeen score fields; this returns the
    composite plus its evidence state. Re-exposing fifteen unevidenced
    sub-scores in a contract built to stop publishing unevidenced numbers would
    defeat its purpose — those return when they carry provenance (plan step D3).

    Descriptive fields are a different matter and are included: a company's
    website, description, sector, city, logo and public/verified flags are not
    assessments and withholding them would be caution without a purpose.
    harm_signals likewise — each carries its own server-authoritative status
    vocabulary (including insufficient_evidence), so it already states its own
    confidence rather than implying one.
    """

    slug = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    sector = serializers.SerializerMethodField()
    country = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    website = serializers.SerializerMethodField()
    logo_url = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    is_public = serializers.SerializerMethodField()
    verified = serializers.SerializerMethodField()
    harm_signals = serializers.SerializerMethodField()

    ecoiq_score = serializers.SerializerMethodField()
    score_status = serializers.SerializerMethodField()
    evidence_coverage = serializers.SerializerMethodField()
    evidence_note = serializers.SerializerMethodField()

    def _state(self, obj):
        cached = getattr(obj, '_v2_score_state', None)
        if cached is None:
            cached = public_score_state(obj)
            obj._v2_score_state = cached
        return cached

    def get_slug(self, obj) -> str:
        return obj.company.slug

    def get_name(self, obj) -> str:
        return obj.company.name

    def get_sector(self, obj) -> str:
        return obj.company.sector

    def get_country(self, obj) -> str:
        return obj.company.country

    def get_city(self, obj) -> str:
        return getattr(obj.company, 'city', '') or ''

    def get_website(self, obj) -> str:
        return getattr(obj.company, 'website', '') or ''

    def get_logo_url(self, obj):
        return getattr(obj.company, 'logo_url', None) or None

    def get_description(self, obj) -> str:
        return getattr(obj.company, 'description', '') or ''

    def get_is_public(self, obj) -> bool:
        return obj.status in ('public', 'verified')

    def get_verified(self, obj) -> bool:
        return bool(obj.is_verified)

    def get_harm_signals(self, obj) -> list:
        """
        Reuses the v1 helper rather than a second implementation — one harm
        vocabulary, one place that produces it.
        """
        from companies.views import _get_harm_signals

        return _get_harm_signals(obj)

    def get_evidence_note(self, obj):
        """
        Human-readable explanation when there is no score, else null.

        Same wording as the web surface, taken from the same constant, so the
        API and the page cannot drift into saying different things.
        """
        state = self._state(obj)
        return None if state.available else state.detail
