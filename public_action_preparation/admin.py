from django.contrib import admin

from public_action_preparation.models import (
    ActionContentDraft, ActionReviewRole, ActionTypeDecision, EthicsReview, FounderActionDecision,
    VerifiedOfficialProcess,
)

admin.site.register(ActionTypeDecision)
admin.site.register(VerifiedOfficialProcess)
admin.site.register(ActionContentDraft)
admin.site.register(EthicsReview)
admin.site.register(ActionReviewRole)
admin.site.register(FounderActionDecision)
