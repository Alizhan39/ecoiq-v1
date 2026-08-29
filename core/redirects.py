"""
core/redirects.py — permanent redirects for public pages the React app replaced.

WHY 301 AND NOT DELETION
------------------------
These URLs were public, some were indexed, and a few are linked from outside.
A 301 tells a crawler the content moved and passes on whatever authority the
old URL had; a 404 throws it away. So every entry here points at a destination
that genuinely covers the same subject.

WHY NOT MORE OF THEM
--------------------
A redirect that lands somewhere unrelated is worse than a 404: the visitor
wanted one thing and silently got another, and a crawler is told two different
URLs are the same page when they are not. Where no React page covers the old
subject, the page is either kept (see the audit) or gated — never redirected
somewhere approximate to make a number smaller.

Named `RedirectView(permanent=True)` rather than middleware so each mapping is
one line in a URLconf, visible next to the routes it replaces.
"""
from __future__ import annotations

#: old public path -> canonical React destination.
#:
#: No chains: every value is a live React route, not another redirect. A test
#: asserts that, because a chain costs a round trip and crawlers give up on
#: long ones.
PERMANENT: dict[str, str] = {
    # How EcoIQ handles evidence, provenance and confidence — which is what the
    # Trust Center now states, against the current architecture rather than the
    # pre-Evidence-Integrity one it was written for.
    '/methodology/': '/trust/',

    # A public index of ~40 "modules", of which platform_registry counts 8 as
    # PRODUCTION and 33 as specification PACKS — documents, not software. An
    # index that lists a specification beside a shipped engine, with no status
    # on either, is the exact confusion Labs exists to remove.
    #
    # Labs is the same index with the registry's real status against every
    # entry, which makes it the honest destination rather than merely a
    # plausible one.
    '/platform/': '/labs/',

    # Stakeholder value framing, no backing capability.
    '/value-distribution/': '/about/',

    # Climate intelligence and stewardship framing, superseded by the
    # Intelligence assessment flow.
    '/stewardship/': '/intelligence/',

    # Visual-intelligence concept pages. Each presented an illustrative
    # analysis of a place or a company; none was generated from the evidence
    # graph, and Intelligence is where a real assessment now lives.
    '/global-intelligence/': '/intelligence/',
    '/kazakhstan-map/': '/intelligence/',
    '/kazakhstan-transition-brief/': '/intelligence/',
    '/khalifa-impact/': '/intelligence/',
    '/sample-report/': '/intelligence/',

    # A third Eco Tours surface. One product, one destination.
    '/khalifa-tours-impact/': '/tours/',

}
