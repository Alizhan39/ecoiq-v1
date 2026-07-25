from django.contrib import admin

from outreach_readiness.models import (
    FounderSendDecision, OutreachCandidateAssessment, OutreachDryRun, OutreachMessageVersion,
    OutreachReviewRole, OutreachRiskReview, OutreachRoute,
)

admin.site.register(OutreachCandidateAssessment)
admin.site.register(OutreachRoute)
admin.site.register(OutreachMessageVersion)
admin.site.register(OutreachRiskReview)
admin.site.register(OutreachDryRun)
admin.site.register(FounderSendDecision)
admin.site.register(OutreachReviewRole)
