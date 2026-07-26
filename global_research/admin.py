from django.contrib import admin

from global_research import models as m


@admin.register(m.ResearchMission)
class ResearchMissionAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'priority', 'required_evidence_level', 'created_at']
    list_filter = ['status', 'priority', 'required_evidence_level']
    search_fields = ['title', 'problem_statement']


@admin.register(m.TechnicalRequirement)
class TechnicalRequirementAdmin(admin.ModelAdmin):
    list_display = ['description', 'mission', 'requirement_type', 'is_mandatory', 'approved', 'version']
    list_filter = ['requirement_type', 'is_mandatory', 'approved']


@admin.register(m.ResearchQueryPlan)
class ResearchQueryPlanAdmin(admin.ModelAdmin):
    list_display = ['mission', 'version', 'freshness_requirement', 'evidence_standard']


@admin.register(m.ResearchSource)
class ResearchSourceAdmin(admin.ModelAdmin):
    list_display = ['title', 'mission', 'source_type', 'evidence_tier', 'source_owner_type', 'status']
    list_filter = ['source_type', 'evidence_tier', 'source_owner_type', 'status', 'language']
    search_fields = ['title', 'publisher']


@admin.register(m.ResearchClaim)
class ResearchClaimAdmin(admin.ModelAdmin):
    list_display = ['subject', 'predicate', 'object_value', 'vendor_provided', 'verified', 'contradiction_status']
    list_filter = ['claim_type', 'vendor_provided', 'verified', 'contradiction_status']
    search_fields = ['subject', 'predicate', 'object_value']


@admin.register(m.ClaimAssessment)
class ClaimAssessmentAdmin(admin.ModelAdmin):
    list_display = ['claim', 'overall_evidence_score', 'status', 'formula_version']


@admin.register(m.TechnologyCategory)
class TechnologyCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'taxonomy_parent', 'maturity_range']


@admin.register(m.TechnologyCandidate)
class TechnologyCandidateAdmin(admin.ModelAdmin):
    list_display = ['name', 'mission', 'category', 'status', 'evidence_score', 'confidence']
    list_filter = ['status', 'commercial_maturity', 'category']


@admin.register(m.ManufacturerProfile)
class ManufacturerProfileAdmin(admin.ModelAdmin):
    list_display = ['organisation', 'headquarters_country', 'company_type', 'verification_status', 'sanctions_screening_status']
    list_filter = ['company_type', 'verification_status', 'sanctions_screening_status']


@admin.register(m.SupplierOrIntegratorProfile)
class SupplierOrIntegratorProfileAdmin(admin.ModelAdmin):
    list_display = ['organisation', 'role_type', 'region', 'verification_status']
    list_filter = ['role_type', 'verification_status']


@admin.register(m.ProductCandidate)
class ProductCandidateAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'manufacturer', 'technology_candidate', 'status', 'indicative_cost_type', 'evidence_score']
    list_filter = ['status', 'lifecycle_status', 'indicative_cost_type']


@admin.register(m.CompatibilityAssessment)
class CompatibilityAssessmentAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'mandatory_pass', 'overall_status', 'assessment_score']
    list_filter = ['mandatory_pass', 'overall_status']


@admin.register(m.ComparativeEvaluation)
class ComparativeEvaluationAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'total_score', 'rank', 'is_ranked']
    list_filter = ['is_ranked', 'reviewer_status']


@admin.register(m.ResearchRecommendation)
class ResearchRecommendationAdmin(admin.ModelAdmin):
    list_display = ['recommendation_type', 'mission', 'human_approval_status', 'confidence']
    list_filter = ['recommendation_type', 'human_approval_status']


@admin.register(m.ContradictionRecord)
class ContradictionRecordAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'resolution_status']
    list_filter = ['contradiction_type', 'resolution_status']


@admin.register(m.SupplyChainRiskFlag)
class SupplyChainRiskFlagAdmin(admin.ModelAdmin):
    list_display = ['risk_type', 'severity', 'mission', 'resolution_status']
    list_filter = ['risk_type', 'severity', 'resolution_status']


@admin.register(m.ResearchRun)
class ResearchRunAdmin(admin.ModelAdmin):
    list_display = ['mission', 'stage', 'started_at', 'completed_at', 'sources_found', 'claims_extracted']
    list_filter = ['stage']


@admin.register(m.ResearchDocumentDraft)
class ResearchDocumentDraftAdmin(admin.ModelAdmin):
    list_display = ['title', 'document_type', 'version', 'status', 'mission']
    list_filter = ['document_type', 'status']


@admin.register(m.ResearchHumanDecision)
class ResearchHumanDecisionAdmin(admin.ModelAdmin):
    list_display = ['stage', 'decision', 'human_approved', 'reviewer', 'decided_at']
    list_filter = ['stage', 'decision']
