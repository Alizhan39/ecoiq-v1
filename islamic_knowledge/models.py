"""Source-bound passages. Editorial publication never approves OS principles."""
import json

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from .catalog import QuranReference, divine_names
from .contracts import Rights, SourceKind, content_hash
from .providers import PROVIDERS, validate_source_url


class KnowledgePassage(models.Model):
    provider = models.CharField(max_length=20, choices=[(key, row['label']) for key, row in PROVIDERS.items()])
    external_id = models.CharField(max_length=160)
    source_url = models.URLField(max_length=1000)
    kind = models.CharField(max_length=40, choices=[(kind.value, kind.value) for kind in SourceKind])
    work = models.CharField(max_length=240)
    edition = models.CharField(max_length=160)
    source_version = models.CharField(max_length=160)
    language = models.CharField(max_length=20)
    attribution = models.CharField(max_length=240)
    passage = models.TextField()
    surah = models.PositiveSmallIntegerField(null=True, blank=True)
    ayah_start = models.PositiveSmallIntegerField(null=True, blank=True)
    ayah_end = models.PositiveSmallIntegerField(null=True, blank=True)
    name_key = models.CharField(max_length=80, blank=True)
    enumeration = models.CharField(max_length=160, blank=True)
    rights = models.CharField(max_length=30, choices=[(right.value, right.value) for right in Rights],
                              default=Rights.PERMISSION_PENDING.value)
    rights_evidence = models.TextField(blank=True)
    digest = models.CharField(max_length=64, editable=False)
    reviewed_digest = models.CharField(max_length=64, blank=True, editable=False)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, editable=False)
    reviewed_at = models.DateTimeField(null=True, blank=True, editable=False)
    revoked = models.BooleanField(default=False)
    embedding = models.JSONField(default=list, blank=True, editable=False)
    embedding_model = models.CharField(max_length=240, blank=True, editable=False)
    embedding_digest = models.CharField(max_length=64, blank=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('provider', 'external_id')
        constraints = [models.UniqueConstraint(fields=('provider', 'external_id'), name='islamic_provider_external_unique')]
        indexes = [models.Index(fields=('provider', 'language'), name='islamic_provider_lang_idx')]

    def __str__(self):
        return f'{self.provider}: {self.external_id}'

    def source_digest(self):
        fields = ('provider', 'external_id', 'source_url', 'kind', 'work', 'edition',
                  'source_version', 'language', 'attribution', 'passage', 'surah',
                  'ayah_start', 'ayah_end', 'name_key', 'enumeration', 'rights', 'rights_evidence')
        return content_hash(json.dumps({key: getattr(self, key) for key in fields},
                                       ensure_ascii=False, sort_keys=True))

    def clean(self):
        super().clean()
        try:
            validate_source_url(self.provider, self.source_url)
            if not isinstance(self.passage, str) or not self.passage.strip() or len(self.passage) > 4000:
                raise ValueError('Passage must contain 1–4000 characters.')
            if self.kind == SourceKind.AI_INFERENCE.value:
                raise ValueError('Provider imports cannot be AI-generated religious content.')
            if self.surah is not None:
                if self.ayah_start is None:
                    raise ValueError('Surah passages require a starting ayah.')
                QuranReference(self.surah, self.ayah_start, self.ayah_end)
            elif self.ayah_start is not None or self.ayah_end is not None:
                raise ValueError('Ayah numbers require a surah.')
            if self.kind in (SourceKind.QURAN.value, SourceKind.TRANSLATION.value) and self.surah is None:
                raise ValueError('Quran and translation passages require a valid ayah reference.')
            if self.name_key and (self.name_key not in divine_names() or not self.enumeration.strip()):
                raise ValueError('Name passages require a known key and explicit provider enumeration.')
            if self.rights != Rights.PERMISSION_PENDING.value and not self.rights_evidence.strip():
                raise ValueError('Publication rights require recorded licence or permission evidence.')
        except (TypeError, ValueError) as exc:
            raise ValidationError(str(exc)) from exc

    def save(self, *args, **kwargs):
        # Partial updates could persist content without its bound digest.
        if kwargs.get('update_fields') is not None:
            raise ValueError('Use a complete save to preserve source/review/embedding bindings.')
        self.full_clean(exclude=('digest',))
        digest = self.source_digest()
        if digest != self.digest:
            self.reviewed_digest = ''
            self.reviewed_by = None
            self.reviewed_at = None
            self.embedding = []
            self.embedding_model = ''
            self.embedding_digest = ''
        self.digest = digest
        super().save(*args, **kwargs)

    @classmethod
    def published(cls):
        return cls.objects.filter(revoked=False, reviewed_digest=F('digest'),
                                  reviewed_at__isnull=False, reviewed_by__isnull=False).exclude(
            Q(rights=Rights.PERMISSION_PENDING.value) | Q(rights_evidence=''))
