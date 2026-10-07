from django.contrib import admin
from django.utils import timezone

from .contracts import Rights
from .models import KnowledgePassage


@admin.register(KnowledgePassage)
class KnowledgePassageAdmin(admin.ModelAdmin):
    list_display = ('provider', 'external_id', 'language', 'kind', 'rights', 'reviewed_at', 'revoked')
    list_filter = ('provider', 'language', 'kind', 'rights', 'revoked')
    search_fields = ('external_id', 'work', 'passage', 'attribution')
    readonly_fields = ('digest', 'reviewed_digest', 'reviewed_by', 'reviewed_at',
                       'embedding', 'embedding_model', 'embedding_digest', 'updated_at')
    actions = ('publish_reviewed', 'withdraw')

    @admin.action(description='Publish selected passages after editorial source/rights review', permissions=['change'])
    def publish_reviewed(self, request, queryset):
        count = 0
        for row in queryset:
            row.full_clean()
            if (row.revoked or row.source_digest() != row.digest
                    or row.rights == Rights.PERMISSION_PENDING.value or not row.rights_evidence.strip()):
                continue
            count += KnowledgePassage.objects.filter(pk=row.pk, digest=row.digest, revoked=False).update(
                reviewed_digest=row.digest, reviewed_by=request.user, reviewed_at=timezone.now())
        self.message_user(request, f'{count} passages published with an editorial review bound to their source digest.')

    @admin.action(description='Withdraw selected passages', permissions=['change'])
    def withdraw(self, request, queryset):
        count = queryset.update(revoked=True, reviewed_digest='', reviewed_by=None, reviewed_at=None)
        self.message_user(request, f'{count} passages withdrawn.')
