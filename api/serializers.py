"""
api/serializers.py — DRF serializers for all EcoIQ API endpoints.
"""
from rest_framework import serializers
from league.models import Company, ScoreHistory


class ScoreHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = ScoreHistory
        fields = ['date', 'ecoiq_score', 'score_pollution_footprint',
                  'score_reduction_progress', 'score_investment',
                  'score_transparency']


class CompanyListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for leaderboard / search results."""
    url = serializers.SerializerMethodField()

    class Meta:
        model  = Company
        fields = [
            'slug', 'name', 'sector', 'country',
            'ecoiq_score', 'rank',
            'ml_score', 'ml_cluster_label', 'is_anomaly',
            'is_public', 'verified',
            'url',
        ]

    def get_url(self, obj) -> str:
        request = self.context.get('request')
        path    = f'/api/v1/companies/{obj.slug}/'
        return request.build_absolute_uri(path) if request else path


class HarmSignalSerializer(serializers.Serializer):
    """Serializes CompanyProfile harm signals."""
    id      = serializers.CharField()
    label   = serializers.CharField()
    status  = serializers.CharField()
    penalty = serializers.IntegerField()
    detail  = serializers.CharField()


class CompanyProfileDetailSerializer(serializers.Serializer):
    """Flat profile pillar scores from CompanyProfile."""
    public_benefit_score               = serializers.FloatField()
    environmental_responsibility_score = serializers.FloatField()
    modernization_score                = serializers.FloatField()
    transparency_anti_corruption_score = serializers.FloatField()
    ethical_alignment_score            = serializers.FloatField()
    anti_corruption_score              = serializers.FloatField()
    harm_penalty                       = serializers.FloatField()
    ecoiq_total_score                  = serializers.FloatField()
    ecoiq_category                     = serializers.CharField()
    moral_label                        = serializers.CharField()
    pollution_level                    = serializers.CharField()
    is_verified                        = serializers.BooleanField()


class CompanyDetailSerializer(serializers.ModelSerializer):
    """Full company profile for the /companies/<slug>/ endpoint."""
    profile     = serializers.SerializerMethodField()
    harm_signals = serializers.SerializerMethodField()
    history     = serializers.SerializerMethodField()
    ml          = serializers.SerializerMethodField()

    class Meta:
        model  = Company
        fields = [
            'slug', 'name', 'sector', 'country', 'city', 'founded_year',
            'website', 'logo_url', 'description',
            'employee_count', 'annual_revenue_usd', 'is_public', 'verified',
            'ecoiq_score', 'rank',
            'score_pollution_footprint', 'score_reduction_progress',
            'score_investment', 'score_transparency', 'score_community_impact',
            'profile', 'harm_signals', 'history', 'ml',
            'created_at', 'updated_at',
        ]

    def get_profile(self, obj) -> dict | None:
        try:
            p = obj.profile
            return CompanyProfileDetailSerializer(p).data
        except Exception:
            return None

    def get_harm_signals(self, obj) -> list:
        try:
            from companies.views import _get_harm_signals
            return _get_harm_signals(obj.profile)
        except Exception:
            return []

    def get_history(self, obj) -> list:
        qs = obj.history.order_by('-date')[:12]
        return ScoreHistorySerializer(qs, many=True).data

    def get_ml(self, obj) -> dict:
        return {
            'ml_score':               obj.ml_score,
            'ml_score_confidence':    obj.ml_score_confidence,
            'ml_predicted_score_12m': obj.ml_predicted_score_12m,
            'ml_cluster':             obj.ml_cluster,
            'ml_cluster_label':       obj.ml_cluster_label,
            'anomaly_score':          obj.anomaly_score,
            'is_anomaly':             obj.is_anomaly,
            'ml_last_run':            obj.ml_last_run,
        }


class CompanyScoresSerializer(serializers.ModelSerializer):
    """Scores-only endpoint for lightweight integration."""
    profile_scores = serializers.SerializerMethodField()
    ml             = serializers.SerializerMethodField()

    class Meta:
        model  = Company
        fields = [
            'slug', 'name',
            'ecoiq_score', 'rank',
            'score_pollution_footprint', 'score_reduction_progress',
            'score_investment', 'score_transparency', 'score_community_impact',
            'profile_scores', 'ml',
        ]

    def get_profile_scores(self, obj) -> dict | None:
        try:
            p = obj.profile
            return {
                'public_benefit_score':               p.public_benefit_score,
                'environmental_responsibility_score': p.environmental_responsibility_score,
                'modernization_score':                p.modernization_score,
                'transparency_anti_corruption_score': p.transparency_anti_corruption_score,
                'ethical_alignment_score':            p.ethical_alignment_score,
                'harm_penalty':                       p.harm_penalty,
                'ecoiq_total_score':                  p.ecoiq_total_score,
            }
        except Exception:
            return None

    def get_ml(self, obj) -> dict:
        return {
            'ml_score':               obj.ml_score,
            'ml_predicted_score_12m': obj.ml_predicted_score_12m,
            'ml_cluster_label':       obj.ml_cluster_label,
            'is_anomaly':             obj.is_anomaly,
        }


class CountryListSerializer(serializers.Serializer):
    """Lightweight country listing."""
    slug         = serializers.CharField()
    name         = serializers.CharField()
    region       = serializers.CharField()
    company_count = serializers.IntegerField()
    avg_ecoiq_score = serializers.FloatField(allow_null=True)


class CountryDetailSerializer(serializers.Serializer):
    """Full country intelligence for /countries/<slug>/."""
    slug          = serializers.CharField()
    name          = serializers.CharField()
    region        = serializers.CharField()
    ai_summary    = serializers.CharField()
    ai_risk_notes = serializers.CharField()
    ecoiq_national_index = serializers.FloatField(allow_null=True)
    company_count        = serializers.IntegerField()
    top_companies        = CompanyListSerializer(many=True)


class LeaderboardSerializer(serializers.ModelSerializer):
    """Leaderboard entry — compact, sortable."""
    class Meta:
        model  = Company
        fields = [
            'rank', 'slug', 'name', 'sector', 'country',
            'ecoiq_score', 'ml_score', 'ml_cluster_label',
            'is_anomaly', 'verified',
        ]
