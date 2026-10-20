"""Project-scoped geological provenance and operational observations.

Raw assay values and drillholes are evidence records, never mineral resources,
reserves or proposed drill targets. This module is imported by models.py so
Django registers the models in the existing gold_intelligence application.
"""
from __future__ import annotations

import re
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from gold_intelligence.services.kpi_definitions import KPI_CHOICES, MINING_KPIS


REVIEW_STATES = [('pending', 'Pending'), ('reviewed', 'Internally reviewed'),
                 ('rejected', 'Rejected')]


def _freeze_approved(instance, *fields):
    """A reviewed claim must be returned to pending before source data changes."""
    if not instance.pk:
        return
    old = type(instance).objects.filter(pk=instance.pk).first()
    if old and old.review_state == 'reviewed' and instance.review_state == 'reviewed':
        if any(getattr(instance, key) != getattr(old, key) for key in fields):
            raise ValidationError('Return a reviewed record to pending before editing its evidence.')


def _review_requirements(item, *, source=None):
    if item.review_state != 'reviewed':
        return
    if not item.reviewer_id or not item.reviewed_at:
        raise ValidationError('Internal review requires a named reviewer and review timestamp.')
    if item.project.is_demo:
        raise ValidationError('Demonstration projects cannot be marked as reviewed evidence.')
    if source is not None and (source.review_state != 'reviewed' or source.is_synthetic):
        raise ValidationError('The underlying source must be reviewed and non-synthetic.')


class GeologicalEvidenceSource(models.Model):
    """One identifiable immutable-source *version*, not an uploaded binary."""
    TYPES = [
        ('map', 'Geological map'), ('geophysics', 'Geophysical survey'),
        ('drill_log', 'Drilling/collar log'), ('assay', 'Laboratory certificate'),
        ('metallurgy', 'Metallurgical study'), ('operations', 'Operations log'),
        ('environment', 'Environment/water'), ('safety', 'Safety log'),
        ('financial', 'Financial record'), ('other', 'Other'),
    ]
    project = models.ForeignKey('gold_intelligence.GoldProject', on_delete=models.PROTECT,
                                related_name='geological_sources')
    source_id = models.CharField(max_length=120)
    kind = models.CharField(max_length=20, choices=TYPES)
    title = models.CharField(max_length=250)
    issuer = models.CharField(max_length=200)
    citation = models.TextField(blank=True)
    source_url = models.URLField(blank=True)
    licence_terms = models.TextField(blank=True)
    observed_on = models.DateField(null=True, blank=True)
    acquired_on = models.DateField(null=True, blank=True)
    crs = models.CharField(max_length=40, blank=True, help_text='Original EPSG code or stated source CRS')
    coverage_notes = models.TextField(blank=True)
    content_sha256 = models.CharField(max_length=64, blank=True,
        help_text='SHA-256 of the original source file, verified off-platform')
    is_synthetic = models.BooleanField(default=False)
    review_state = models.CharField(max_length=10, choices=REVIEW_STATES, default='pending')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                  on_delete=models.SET_NULL, related_name='+')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['project', 'source_id'], name='uniq_gold_source_version')]
        ordering = ['project', 'source_id']

    def __str__(self):
        return f'{self.source_id} — {self.title}'

    def clean(self):
        super().clean()
        if self.content_sha256 and not re.fullmatch(r'[0-9a-f]{64}', self.content_sha256):
            raise ValidationError({'content_sha256': 'Expected lowercase hex SHA-256 (64 characters).'})
        _review_requirements(self)
        if self.review_state == 'reviewed':
            if not (self.citation.strip() and self.content_sha256 and self.licence_terms.strip()):
                raise ValidationError('Reviewed sources require citation, file hash and data rights terms.')
            if self.is_synthetic:
                raise ValidationError('Synthetic datasets cannot be reviewed as real evidence.')

    def save(self, *args, **kwargs):
        _freeze_approved(self, 'project_id', 'source_id', 'kind', 'issuer', 'citation',
                         'source_url', 'licence_terms', 'observed_on', 'crs',
                         'content_sha256', 'is_synthetic')
        self.full_clean()
        return super().save(*args, **kwargs)


class GoldDrillhole(models.Model):
    """WGS84 collar only: do not accept UTM coordinates without reprojection."""
    project = models.ForeignKey('gold_intelligence.GoldProject', on_delete=models.PROTECT,
                                related_name='drillholes')
    source = models.ForeignKey(GeologicalEvidenceSource, on_delete=models.PROTECT,
                               related_name='drillholes')
    hole_id = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    total_depth_m = models.DecimalField(max_digits=12, decimal_places=3)
    collar_elevation_m = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    logged_on = models.DateField(null=True, blank=True)
    review_state = models.CharField(max_length=10, choices=REVIEW_STATES, default='pending')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                  on_delete=models.SET_NULL, related_name='+')
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['project', 'hole_id'], name='uniq_gold_hole_by_project')]
        ordering = ['project', 'hole_id']

    def clean(self):
        super().clean()
        if self.source_id and self.project_id and self.source.project_id != self.project_id:
            raise ValidationError('Drillhole/source project mismatch.')
        if self.source_id and self.source.kind != 'drill_log':
            raise ValidationError('Collar coordinates must reference a drilling/collar log.')
        if self.latitude is not None and not (Decimal('-90') <= self.latitude <= Decimal('90')):
            raise ValidationError('Latitude must be WGS84 in [-90, 90].')
        if self.longitude is not None and not (Decimal('-180') <= self.longitude <= Decimal('180')):
            raise ValidationError('Longitude must be WGS84 in [-180, 180].')
        if self.total_depth_m is not None and self.total_depth_m <= 0:
            raise ValidationError('Hole depth must be positive.')
        if self.source_id:
            _review_requirements(self, source=self.source)

    def save(self, *args, **kwargs):
        _freeze_approved(self, 'project_id', 'source_id', 'hole_id', 'latitude',
                         'longitude', 'total_depth_m', 'collar_elevation_m', 'logged_on')
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.hole_id


class GoldAssayInterval(models.Model):
    """Laboratory interval; a grade alone cannot establish a resource or reserve."""
    SAMPLE_TYPES = [('primary', 'Primary sample'), ('blank', 'Blank'),
                    ('standard', 'Reference standard'), ('duplicate', 'Duplicate')]
    project = models.ForeignKey('gold_intelligence.GoldProject', on_delete=models.PROTECT,
                                related_name='assays')
    drillhole = models.ForeignKey(GoldDrillhole, on_delete=models.PROTECT, related_name='assays')
    source = models.ForeignKey(GeologicalEvidenceSource, on_delete=models.PROTECT,
                               related_name='assays')
    sample_id = models.CharField(max_length=120)
    sample_type = models.CharField(max_length=12, choices=SAMPLE_TYPES, default='primary')
    from_m = models.DecimalField(max_digits=12, decimal_places=3)
    to_m = models.DecimalField(max_digits=12, decimal_places=3)
    au_g_per_t = models.DecimalField(max_digits=17, decimal_places=6, null=True, blank=True)
    laboratory = models.CharField(max_length=200, blank=True)
    certificate_id = models.CharField(max_length=160, blank=True)
    review_state = models.CharField(max_length=10, choices=REVIEW_STATES, default='pending')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                  on_delete=models.SET_NULL, related_name='+')
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['project', 'sample_id', 'source'],
                                                name='uniq_gold_sample_source')]
        ordering = ['project', 'drillhole', 'from_m']

    def clean(self):
        super().clean()
        if self.project_id and self.drillhole_id and self.drillhole.project_id != self.project_id:
            raise ValidationError('Assay/drillhole project mismatch.')
        if self.source_id and self.project_id and self.source.project_id != self.project_id:
            raise ValidationError('Assay/source project mismatch.')
        if self.source_id and self.source.kind != 'assay':
            raise ValidationError('An assay interval requires a laboratory certificate source.')
        if self.from_m is not None and self.to_m is not None:
            if self.from_m < 0 or self.to_m <= self.from_m:
                raise ValidationError('Assay interval requires 0 <= from_m < to_m.')
            if self.drillhole_id and self.to_m > self.drillhole.total_depth_m:
                raise ValidationError('Interval extends beyond logged drillhole depth.')
        if self.au_g_per_t is not None and self.au_g_per_t < 0:
            raise ValidationError('Gold grade must be >= 0 g/t, or null if unmeasured.')
        if self.source_id:
            _review_requirements(self, source=self.source)
        if self.review_state == 'reviewed':
            if self.drillhole.review_state != 'reviewed' or not (
                self.certificate_id and self.laboratory and self.au_g_per_t is not None
            ):
                raise ValidationError('Review requires a reviewed drillhole, lab, certificate and assay result.')

    def save(self, *args, **kwargs):
        _freeze_approved(self, 'project_id', 'drillhole_id', 'source_id', 'sample_id',
                         'sample_type', 'from_m', 'to_m', 'au_g_per_t',
                         'laboratory', 'certificate_id')
        self.full_clean()
        return super().save(*args, **kwargs)


class MineKPIObservation(models.Model):
    """Raw period-matched quantities; calculations and units belong to code registry."""
    project = models.ForeignKey('gold_intelligence.GoldProject', on_delete=models.PROTECT,
                                related_name='mine_kpi_observations')
    source = models.ForeignKey(GeologicalEvidenceSource, on_delete=models.PROTECT,
                               related_name='mine_kpi_observations')
    metric_key = models.CharField(max_length=50, choices=KPI_CHOICES)
    period_start = models.DateField()
    period_end = models.DateField()
    numerator = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    denominator = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    review_state = models.CharField(max_length=10, choices=REVIEW_STATES, default='pending')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                  on_delete=models.SET_NULL, related_name='+')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    method_version = models.CharField(max_length=12, default='1')
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=['project', 'source', 'metric_key', 'period_start', 'period_end'],
            name='uniq_gold_kpi_observation')]
        ordering = ['project', 'metric_key', '-period_end']

    def clean(self):
        super().clean()
        if self.source_id and self.project_id and self.source.project_id != self.project_id:
            raise ValidationError('KPI/source project mismatch.')
        if self.period_start and self.period_end and self.period_end < self.period_start:
            raise ValidationError('KPI period end cannot precede start.')
        if self.numerator is not None and self.numerator < 0:
            raise ValidationError('Numerator cannot be negative.')
        if self.denominator is not None and self.denominator <= 0:
            raise ValidationError('Denominator must be positive.')
        definition = MINING_KPIS.get(self.metric_key)
        if definition and self.method_version != definition.method_version:
            raise ValidationError('KPI calculation version is not supported by the current registry.')
        if self.source_id:
            _review_requirements(self, source=self.source)
        if self.review_state == 'reviewed' and (self.numerator is None or self.denominator is None):
            raise ValidationError('Complete raw quantities are required before KPI review.')
        if definition and definition.percent and self.numerator is not None and self.denominator:
            if self.numerator > self.denominator:
                raise ValidationError('Percentage KPI numerator cannot exceed its denominator.')

    def save(self, *args, **kwargs):
        _freeze_approved(self, 'project_id', 'source_id', 'metric_key',
                         'period_start', 'period_end', 'numerator', 'denominator',
                         'method_version')
        self.full_clean()
        return super().save(*args, **kwargs)
