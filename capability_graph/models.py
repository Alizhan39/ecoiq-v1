"""
capability_graph/models.py — the evidence-backed Capability Graph.

Replaces the flat "organisation/contact directory" pattern (good_agents'
`ResponsibleParty` used to store a bare name + guessed party_type per
opportunity — the same real organisation re-created as a fresh row every
time a new opportunity happened to mention it, e.g. ten separate "USGS"
rows). The graph this app defines is the reusable node/edge structure
underneath that:

    REAL-WORLD NEED -> REQUIRED CAPABILITY -> ORGANISATION WITH
    EVIDENCE-BACKED CAPABILITY -> VERIFIED PUBLIC ROUTE -> HUMAN-GOVERNED
    ACTION

`Organisation` is the ONE deduplicated node for a real-world org (a
company, a government department, a charity, a regulator, a fund, ...).
`OrganisationCapability` is the evidence-backed edge: a specific,
scoped claim that a specific organisation can perform a specific
capability, in a specific jurisdiction, for a specific topic/domain, with
an evidence source, a verification state, and its own real limitations —
never a guess inferred from the organisation's name or sector alone (see
each field's docstring below). `PublicRoute` is how a human actually
reaches that capability (an application URL, a public contact channel) —
kept separate from the capability claim itself so a real capability with
no known route yet stays honestly represented (route-less, not "unusable"
— the two are different facts).

"REQUIRED CAPABILITY" (the second node in the chain) and "HUMAN-GOVERNED
ACTION" (the fifth) are NOT modelled here as their own tables: the first
is a deterministic mapping over an existing Need/Opportunity's own fields
(see `services/needs.py` — plain code, not a new table, exactly like
PR3's keyword-overlap scoring), and the second is the ALREADY-BUILT
governed action pipeline from PR5 (ActionGate/ActionPathway/OutreachDraft/
ConnectionCandidate) — this app deliberately does not duplicate it. This
keeps the graph to the minimum needed to route a real action, not a
general-purpose knowledge graph (see docs/CAPABILITY_GRAPH.md).
"""
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


ORG_TYPE_CHOICES = [
    ('local_authority', 'Local authority'), ('government_department', 'Government department'),
    ('company', 'Company'), ('charity', 'Charity'), ('ngo', 'NGO'),
    ('community_organisation', 'Community organisation'), ('funder', 'Funder'),
    ('research_institution', 'Research institution'), ('facility_operator', 'Facility operator'),
    ('regulator', 'Regulator'), ('internal_ecoiq_team', 'Internal EcoIQ team'), ('other', 'Other'),
]

# The fixed capability vocabulary from the brief. A CharField with choices,
# not a separate lookup table — the list is small, stable, and doesn't need
# its own admin-managed rows; keeping it a table would be exactly the kind
# of extra generality this app is told not to build.
CAPABILITY_CHOICES = [(v, v.replace('_', ' ').title()) for v in [
    'fund', 'grant', 'lend', 'donate', 'regulate', 'authorise', 'permit', 'procure',
    'install', 'transport', 'collect', 'recycle', 'reuse', 'supply', 'manufacture',
    'provide_technology', 'provide_expertise', 'research', 'verify', 'audit', 'measure',
    'host', 'train', 'employ', 'refer', 'coordinate', 'respond_to_emergency',
]]

# Mirrors the ESTIMATED/TARGET/MEASURED/VERIFIED discipline used everywhere
# else in this project (see good_agents' evidence-quality vocabulary).
# Deliberately conservative default ('unverified') — a capability claim
# never starts life looking more solid than it is.
VERIFICATION_STATE_CHOICES = [
    ('unverified', 'Unverified — not yet checked against any real source'),
    ('self_reported', 'Self-reported — the organisation itself claims this, unconfirmed'),
    ('documented', 'Documented — a real public source states this'),
    ('independently_verified', 'Independently verified — a human confirmed this directly'),
]

ROUTE_TYPE_CHOICES = [
    ('online_application', 'Online application'), ('public_contact_form', 'Public contact form'),
    ('email', 'Email'), ('phone', 'Phone'), ('referral_required', 'Referral required'),
    ('in_person', 'In person'), ('other', 'Other'),
]


class Organisation(models.Model):
    """
    The ONE node for a real-world organisation — never duplicated per
    opportunity, mission, or funding match. `dedupe_key` is a normalised
    form of `name` (+ jurisdiction) used by
    `services.organisations.get_or_create_organisation()`, the ONLY
    sanctioned way to create a row here, so "USGS" and "usgs" (or the same
    org resolved from two different signals) never become two rows.
    """
    name = models.CharField(max_length=255)
    org_type = models.CharField(max_length=24, choices=ORG_TYPE_CHOICES, default='other')
    jurisdiction = models.CharField(
        max_length=150, blank=True,
        help_text='Free-text jurisdiction/geography this organisation is known to operate in overall '
                   '(e.g. "England", "Global", "Kazakhstan") — a specific capability may still be scoped '
                   'narrower via OrganisationCapability.jurisdiction.',
    )
    # Soft, optional link to the real tracked-company model — never a hard
    # dependency (most capability-holding orgs relevant to Good Agents are
    # NOT companies: government departments, regulators, charities, funds).
    linked_company = models.ForeignKey(
        'companies.CompanyProfile', null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    website = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    dedupe_key = models.CharField(max_length=300, unique=True, editable=False)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.dedupe_key:
            self.dedupe_key = f'{slugify(self.name)}::{slugify(self.jurisdiction)}'
        super().save(*args, **kwargs)


class OrganisationCapability(models.Model):
    """
    The evidence-backed edge: a specific, scoped claim that `organisation`
    can perform `capability`. Every field here exists because a real
    capability claim is NEVER just "this org does X" — see the brief's own
    examples (a local authority's regulatory authority may not extend to
    every jurisdiction; a charity supporting a cause may not fund it
    directly; a manufacturer may not install its own product; a fund may
    not accept unsolicited applications). `capability` is never set from
    the organisation's name or sector alone — every row must cite
    `evidence_source`/`evidence_url`.
    """
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='capabilities')
    capability = models.CharField(max_length=24, choices=CAPABILITY_CHOICES)

    # Where/what this capability applies to — kept separate from
    # Organisation.jurisdiction because an org's OVERALL jurisdiction and
    # ONE capability's actual scope can genuinely differ (a national
    # regulator with a capability that's only devolved in one region).
    jurisdiction = models.CharField(max_length=150, blank=True)
    topic_domain = models.CharField(
        max_length=150, blank=True,
        help_text='Free-text topic/domain this capability applies to (e.g. "flood risk", "heat pumps", '
                   '"seismic monitoring") — never inferred from the organisation\'s sector alone.',
    )

    # Evidence — a soft pointer (same convention as
    # evidence_memory.EvidenceMemory.source_reference) plus, when the
    # evidence is a public webpage/API, its real URL.
    evidence_source = models.CharField(max_length=300, blank=True)
    evidence_url = models.URLField(blank=True)

    verification_state = models.CharField(max_length=24, choices=VERIFICATION_STATE_CHOICES, default='unverified')
    last_verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )

    # Never optional in spirit — a real capability claim almost always has
    # a real limitation worth stating (see the brief's own examples). Left
    # blank=True at the DB level rather than enforced, since a genuinely
    # unlimited capability is possible; empty is rendered as an honest
    # "No limitations recorded" at display time, never fabricated.
    limitations = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['organisation__name', 'capability']
        unique_together = [('organisation', 'capability', 'jurisdiction', 'topic_domain')]

    def __str__(self):
        return f'{self.organisation} — {self.get_capability_display()} ({self.jurisdiction or "no jurisdiction set"})'


class PublicRoute(models.Model):
    """
    HOW a human actually engages a capability — distinct from whether the
    capability exists at all. A capability can be real and evidence-backed
    with NO known route yet (route-less is an honest, valid state, not an
    error). `route_value` must come from real evidence (the parent
    capability's own evidence_url, or independently sourced) — never
    guessed or inferred, per the brief's "no guessed contact details" rule.
    """
    organisation_capability = models.ForeignKey(
        OrganisationCapability, on_delete=models.CASCADE, related_name='public_routes',
    )
    route_type = models.CharField(max_length=24, choices=ROUTE_TYPE_CHOICES)
    route_value = models.CharField(max_length=500, help_text='The real URL, email, or phone number — never inferred.')
    is_currently_open = models.BooleanField(
        default=True, help_text='Some routes (e.g. grant application windows) are only open at certain times.',
    )
    notes = models.TextField(blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['organisation_capability', 'route_type']

    def __str__(self):
        return f'{self.get_route_type_display()} — {self.organisation_capability}'
