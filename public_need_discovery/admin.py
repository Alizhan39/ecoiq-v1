from django.contrib import admin

from public_need_discovery.models import CandidateOrganisationRole, PilotCandidateAssessment, ProviderRunMetrics

admin.site.register(PilotCandidateAssessment)
admin.site.register(CandidateOrganisationRole)
admin.site.register(ProviderRunMetrics)
