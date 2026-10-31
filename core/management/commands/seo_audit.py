"""
Management command: seo_audit

Runs EcoIQ's technical SEO checks against *this* repository and Django
configuration. Everything it reports is derived from a real file, a real URL
resolution, or a real rendered response — nothing is inferred from a
convention or assumed from a template name.

It is deliberately offline. It renders `robots.txt` and `sitemap.xml` through
Django's own test client and reads templates and static files from disk. It
never fetches https://ecoiq.uk, so it cannot fabricate a "live production"
result it has no access to. Production-only checks (indexing status, Core Web
Vitals, backlinks) are out of scope and are listed as such by --explain.

Usage:
    python manage.py seo_audit
    python manage.py seo_audit --strict     # exit 1 if any ERROR finding
    python manage.py seo_audit --explain    # also print what is NOT checked

Paired skill: .claude/skills/ecoiq-seo-audit/SKILL.md
"""
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.template.loader import get_template
from django.test import Client
from django.urls import NoReverseMatch, reverse

ERROR = 'ERROR'
WARN = 'WARN'
OK = 'OK'

# Meta tags base.html is expected to define for every page. Each entry is
# (human label, regex that must match the rendered/base template source).
REQUIRED_HEAD_TAGS = [
    ('viewport meta', r'<meta\s+name=["\']viewport["\']'),
    ('title block', r'<title>'),
    ('meta description', r'<meta\s+name=["\']description["\']'),
    ('canonical link', r'<link\s+rel=["\']canonical["\']'),
    ('og:title', r'property=["\']og:title["\']'),
    ('og:description', r'property=["\']og:description["\']'),
    ('og:image', r'property=["\']og:image["\']'),
    ('og:url', r'property=["\']og:url["\']'),
    ('og:type', r'property=["\']og:type["\']'),
]

# Static assets referenced from a hard-coded absolute URL in a template are
# invisible to {% static %} and to collectstatic's manifest, so a rename
# silently 404s. This finds them and checks each one exists on disk.
ABSOLUTE_STATIC_RE = re.compile(r'https?://[^"\'\s]*?/static/([^"\'\s>]+)')


class Finding:
    __slots__ = ('level', 'check', 'message', 'evidence')

    def __init__(self, level, check, message, evidence=''):
        self.level = level
        self.check = check
        self.message = message
        self.evidence = evidence


class Command(BaseCommand):
    help = 'Audit EcoIQ technical SEO: robots, sitemap, metadata, canonical, OG, structured data, hreflang.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--strict', action='store_true',
            help='Exit with status 1 if any ERROR-level finding is reported.',
        )
        parser.add_argument(
            '--explain', action='store_true',
            help='Also print the checks this command deliberately does not perform.',
        )

    # ── entry point ──────────────────────────────────────────────────────────

    def handle(self, *args, **options):
        findings = run_audit()

        counts = {ERROR: 0, WARN: 0, OK: 0}
        for f in findings:
            counts[f.level] = counts.get(f.level, 0) + 1

        for f in findings:
            style = {
                ERROR: self.style.ERROR,
                WARN: self.style.WARNING,
                OK: self.style.SUCCESS,
            }[f.level]
            self.stdout.write(style(f'[{f.level:5}] {f.check}: {f.message}'))
            if f.evidence:
                self.stdout.write(f'         └─ {f.evidence}')

        self.stdout.write('')
        self.stdout.write(
            f'{counts[OK]} passed, {counts[WARN]} warnings, {counts[ERROR]} errors'
        )

        if options['explain']:
            self.stdout.write('')
            self.stdout.write('Not checked here (needs live production access or a paid API):')
            for line in NOT_CHECKED:
                self.stdout.write(f'  · {line}')

        if options['strict'] and counts[ERROR]:
            # Non-zero exit so CI can gate on it.
            raise SystemExit(1)


NOT_CHECKED = [
    'Actual index coverage in Google/Bing (needs Search Console credentials).',
    'Core Web Vitals / field data (needs CrUX or a live crawl).',
    'Backlinks and referring domains (needs a paid third-party API).',
    'Live redirect chains on the production domain (needs network access).',
    'Rendered-JS content parity (islands hydrate client-side; needs a browser).',
]


# ── the checks ───────────────────────────────────────────────────────────────

def run_audit():
    """Return a list of Finding. Importable so tests can assert on it."""
    findings = []
    findings += _check_robots()
    findings += _check_sitemap()
    findings += _check_head_tags()
    findings += _check_absolute_static_refs()
    findings += _check_canonical_host()
    findings += _check_hreflang_matches_languages()
    findings += _check_structured_data()
    findings += _check_robots_vs_sitemap_conflict()
    return findings


def _client():
    # ALLOWED_HOSTS here is environment-driven, and `testserver` (the test
    # client's default) is only auto-allowed while a test runner is active —
    # running this command directly would 400 on DisallowedHost. Use a host the
    # project already allows, falling back to the test default.
    allowed = [h for h in getattr(settings, 'ALLOWED_HOSTS', []) if h not in ('*',)]
    return Client(SERVER_NAME=allowed[0] if allowed else 'testserver')


def _render_robots():
    try:
        response = _client().get('/robots.txt')
    except Exception as exc:  # pragma: no cover - defensive
        return None, str(exc)
    if response.status_code != 200:
        return None, f'HTTP {response.status_code}'
    return response.content.decode('utf-8', 'replace'), ''


def _robots_groups(body):
    """Parse robots.txt into {user-agent: [disallow rules]}.

    Group-awareness matters: EcoIQ deliberately blocks Bytespider, CCBot and
    PetalBot entirely with `Disallow: /` inside their own groups. Treating
    those as a site-wide de-index would be a false positive, and conversely a
    per-bot rule must not be used to judge the sitemap.
    """
    groups = {}
    current = []
    expecting_agents = False
    for raw in body.splitlines():
        line = raw.split('#', 1)[0].strip()
        if not line or ':' not in line:
            continue
        field, value = (part.strip() for part in line.split(':', 1))
        field = field.lower()
        if field == 'user-agent':
            if not expecting_agents:
                current = []
                expecting_agents = True
            current.append(value.lower())
            groups.setdefault(value.lower(), [])
        elif field == 'disallow':
            expecting_agents = False
            for agent in current:
                if value:
                    groups.setdefault(agent, []).append(value)
        else:
            expecting_agents = False
    return groups


def _check_robots():
    body, error = _render_robots()
    if body is None:
        return [Finding(ERROR, 'robots.txt', 'does not serve successfully', error)]

    out = [Finding(OK, 'robots.txt', 'serves at /robots.txt')]

    if not re.search(r'^\s*Sitemap:\s*\S+', body, re.MULTILINE | re.IGNORECASE):
        out.append(Finding(
            ERROR, 'robots.txt',
            'no Sitemap: directive — crawlers must be told where the sitemap is',
        ))
    else:
        out.append(Finding(OK, 'robots.txt', 'declares a Sitemap: directive'))

    if not re.search(r'^\s*User-agent:\s*\*', body, re.MULTILINE | re.IGNORECASE):
        out.append(Finding(WARN, 'robots.txt', 'no wildcard User-agent: * group'))

    # A blanket disallow only de-indexes the site if it is in the wildcard
    # group. Per-bot `Disallow: /` blocks (Bytespider, CCBot, PetalBot here)
    # are deliberate and correct.
    groups = _robots_groups(body)
    if '/' in groups.get('*', []):
        out.append(Finding(
            ERROR, 'robots.txt',
            'the User-agent: * group contains "Disallow: /" — this de-indexes the whole site',
        ))
    else:
        blocked = sorted(a for a, rules in groups.items() if a != '*' and '/' in rules)
        out.append(Finding(
            OK, 'robots.txt',
            'wildcard group is not blanket-disallowed',
            f'fully blocked bots: {", ".join(blocked)}' if blocked else '',
        ))
    return out


def _check_sitemap():
    try:
        response = _client().get('/sitemap.xml')
    except Exception as exc:  # pragma: no cover - defensive
        return [Finding(ERROR, 'sitemap.xml', 'raised while rendering', str(exc))]

    if response.status_code != 200:
        return [Finding(
            ERROR, 'sitemap.xml',
            f'does not serve successfully (HTTP {response.status_code})',
        )]

    body = response.content.decode('utf-8', 'replace')
    url_count = body.count('<url>')
    out = [Finding(OK, 'sitemap.xml', f'serves with {url_count} URL(s)')]
    if url_count == 0:
        out.append(Finding(
            WARN, 'sitemap.xml',
            'contains zero URLs — expected on an empty database, a real problem otherwise',
        ))

    # Every static page the sitemap advertises must actually reverse.
    from companies.sitemaps import StaticSitemap
    for name in StaticSitemap._pages:
        try:
            reverse(name)
        except NoReverseMatch:
            out.append(Finding(
                ERROR, 'sitemap.xml',
                f'advertises URL name "{name}" which no longer resolves',
                'companies/sitemaps.py StaticSitemap._pages',
            ))
    return out


def _base_template_source():
    template = get_template('base.html')
    return Path(template.origin.name).read_text(encoding='utf-8')


def _check_head_tags():
    source = _base_template_source()
    out = []
    for label, pattern in REQUIRED_HEAD_TAGS:
        if re.search(pattern, source, re.IGNORECASE):
            out.append(Finding(OK, 'head metadata', f'{label} present in base.html'))
        else:
            out.append(Finding(ERROR, 'head metadata', f'{label} missing from base.html'))

    if not re.search(r'name=["\']twitter:card["\']', source, re.IGNORECASE):
        out.append(Finding(
            WARN, 'head metadata',
            'no twitter:card meta — X/Twitter falls back to a small preview',
            'templates/base.html',
        ))
    return out


def _static_source_dirs():
    dirs = [Path(p) for p in getattr(settings, 'STATICFILES_DIRS', [])]
    root = getattr(settings, 'STATIC_ROOT', None)
    if root:
        dirs.append(Path(root))
    return [d for d in dirs if d.exists()]


def _check_absolute_static_refs():
    """Hard-coded https://host/static/... references bypass {% static %}, so a
    missing file 404s silently. Check every one that appears in a template."""
    template_root = Path(settings.BASE_DIR) / 'templates'
    static_dirs = _static_source_dirs()
    out = []
    seen = set()

    for path in sorted(template_root.rglob('*.html')):
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):  # pragma: no cover - defensive
            continue
        for match in ABSOLUTE_STATIC_RE.finditer(text):
            relative = match.group(1)
            key = relative
            if key in seen:
                continue
            seen.add(key)
            if any((d / relative).exists() for d in static_dirs):
                out.append(Finding(
                    OK, 'static asset', f'{relative} exists',
                ))
            else:
                out.append(Finding(
                    ERROR, 'static asset',
                    f'{relative} is referenced by an absolute URL but does not exist',
                    f'first seen in {path.relative_to(settings.BASE_DIR)}',
                ))
    if not seen:
        out.append(Finding(OK, 'static asset', 'no hard-coded absolute /static/ URLs in templates'))
    return out


def _check_canonical_host():
    source = _base_template_source()
    # Stop the host capture at `{` too — these hrefs are Django templates, e.g.
    # href="https://ecoiq.uk{{ request.path }}", with no slash after the host.
    hosts = set(re.findall(
        r'<link\s+rel=["\']canonical["\']\s+href=["\'](https?://[^/{"\']+)', source, re.IGNORECASE,
    ))
    og_hosts = set(re.findall(
        r'property=["\']og:url["\']\s+content=["\'](https?://[^/{"\']+)', source, re.IGNORECASE,
    ))
    out = []
    if len(hosts) > 1:
        out.append(Finding(
            ERROR, 'canonical', f'base.html uses more than one canonical host: {sorted(hosts)}',
        ))
    elif hosts:
        out.append(Finding(OK, 'canonical', f'single canonical host {hosts.pop()}'))

    if og_hosts and hosts and og_hosts != hosts:
        out.append(Finding(
            WARN, 'canonical', 'og:url host differs from the canonical host',
        ))
    return out


def _check_hreflang_matches_languages():
    source = _base_template_source()
    has_hreflang = bool(re.search(r'hreflang=', source, re.IGNORECASE))
    enabled = [code for code, _ in getattr(settings, 'LANGUAGES', [])]

    if len(enabled) <= 1 and has_hreflang:
        return [Finding(
            ERROR, 'hreflang',
            f'hreflang tags are emitted but only {enabled} is enabled in LANGUAGES',
        )]
    if len(enabled) > 1 and not has_hreflang:
        return [Finding(
            ERROR, 'hreflang',
            f'{len(enabled)} languages enabled ({enabled}) but no hreflang tags — '
            'translated pages will compete with each other',
        )]
    if len(enabled) <= 1:
        return [Finding(
            OK, 'hreflang',
            f'single-language site ({enabled}); no hreflang needed — correct',
        )]
    return [Finding(OK, 'hreflang', 'hreflang present and multiple languages enabled')]


def _check_structured_data():
    template_root = Path(settings.BASE_DIR) / 'templates'
    with_ld = [
        p.relative_to(template_root)
        for p in sorted(template_root.rglob('*.html'))
        if 'application/ld+json' in p.read_text(encoding='utf-8', errors='replace')
    ]
    if not with_ld:
        return [Finding(
            WARN, 'structured data',
            'no JSON-LD anywhere — entity pages benefit from Organization/Dataset markup',
        )]
    return [Finding(
        OK, 'structured data',
        f'JSON-LD present in {len(with_ld)} template(s)',
        ', '.join(str(p) for p in with_ld[:5]),
    )]


def _check_robots_vs_sitemap_conflict():
    """A URL that is both advertised in the sitemap and disallowed in robots.txt
    is a direct contradiction — the crawler is told to fetch and not to fetch."""
    body, _ = _render_robots()
    if body is None:
        return []

    # Only the wildcard group decides whether a sitemap URL is crawlable by
    # search engines generally — a rule aimed at one bot is not a conflict.
    disallowed = _robots_groups(body).get('*', [])
    if not disallowed:
        return []

    try:
        response = _client().get('/sitemap.xml')
        sitemap_body = response.content.decode('utf-8', 'replace')
    except Exception:  # pragma: no cover - defensive
        return []

    locs = re.findall(r'<loc>([^<]+)</loc>', sitemap_body)
    conflicts = []
    for loc in locs:
        path = re.sub(r'^https?://[^/]+', '', loc)
        for rule in disallowed:
            if rule != '/' and path.startswith(rule.rstrip('*')):
                conflicts.append((path, rule))
                break

    if conflicts:
        return [Finding(
            ERROR, 'robots vs sitemap',
            f'{len(conflicts)} sitemap URL(s) are disallowed in robots.txt',
            f'e.g. {conflicts[0][0]} blocked by "Disallow: {conflicts[0][1]}"',
        )]
    return [Finding(OK, 'robots vs sitemap', 'no sitemap URL is blocked by robots.txt')]
