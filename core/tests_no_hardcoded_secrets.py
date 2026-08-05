"""
Repository guard against hardcoded sensitive configuration.

Gitleaks passed its first real run, but its default rules did not flag the
historical administrator password that caused this remediation: those rules
target high-entropy, provider-shaped credentials (AWS keys, GitHub tokens), not
a human-chosen password literal such as the one that sat in
`core/management/commands/bootstrap_superuser.py`.

This test closes that specific gap. It scans tracked source and deployment
configuration for sensitive names assigned a non-empty literal, and accepts the
safe forms: environment lookups, secret-manager references, and empty or
clearly-marked test placeholders.

Deliberately narrow. It checks a fixed list of sensitive names rather than
guessing at entropy, so it produces no noise and needs no allowlist. It does
not scan migrations, vendored code, fixtures, or generated assets — those do not
carry runtime configuration, and including them only produces false positives.

It never prints a matched value: failures report file, line and variable name.
"""
import re
import subprocess
from pathlib import Path

from django.test import SimpleTestCase

REPO_ROOT = Path(__file__).resolve().parent.parent

# Name fragments that must never be assigned a literal secret. Fragments, not
# exact names: the historical defect was `_DEFAULT_PASSWORD = '…'`, which an
# exact-match list of BOOTSTRAP_ADMIN_PASSWORD/ADMIN_PASSWORD would have missed
# entirely — the same blind spot that let it reach production.
SENSITIVE_NAMES = (
    'PASSWORD',
    'PASSWD',
    'SECRET_KEY',
    'API_KEY',
    'APIKEY',
    'ACCESS_TOKEN',
    'AUTH_TOKEN',
    'PRIVATE_KEY',
)

# Python/YAML/shell assignment of a sensitive name to a quoted literal.
_ASSIGN = re.compile(
    r'(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*(?P<quote>["\'])(?P<value>.*?)(?P=quote)'
)

# Values that are safe even though they are literals.
_SAFE_VALUE = re.compile(
    r'''^(
        |                                   # empty
        \s*|                                # whitespace only
        (?:django-insecure-)[\w\-]*|        # Django's own dev-key marker
        \$\{?[A-Za-z_][A-Za-z0-9_]*\}?|     # ${VAR} / $VAR indirection
        (?:sync:\s*)?false|                 # render.yaml sync flags
        .*(?:example|placeholder|changeme|your[-_]|<[^>]+>).*   # documented placeholders
    )$''',
    re.X | re.I,
)

# A line is safe when the name is bound to an environment or secret lookup.
_SAFE_LOOKUP = re.compile(
    r'os\.environ|os\.getenv|environ\.get|getenv\(|'
    r'get_secret|secretmanager|sync:\s*false|fromDatabase|generateValue',
    re.I,
)

SCANNED_SUFFIXES = ('.py', '.yml', '.yaml', '.sh', '.toml', '.cfg', '.ini')

EXCLUDED_PARTS = (
    '/migrations/', '/node_modules/', '/static/dist/', '/staticfiles/',
    '/fixtures/', '/.venv/', '/venv/', '/frontend/', '/locale/',
)

# Test modules legitimately assign fabricated credentials to exercise code
# paths; they are fixtures in all but name. Scanning them produces noise, not
# signal — the incident this guard exists for was in runtime code
# (core/management/commands/bootstrap_superuser.py), which IS scanned.
TEST_FILE_MARKERS = ('/tests.py', '/tests_', '/test_', '/tests/', '/conftest.py')


def tracked_files():
    out = subprocess.run(
        ['git', 'ls-files'], cwd=REPO_ROOT, capture_output=True, text=True, timeout=60)
    out.check_returncode()
    for rel in out.stdout.splitlines():
        if not rel.endswith(SCANNED_SUFFIXES):
            continue
        marked = f'/{rel}'
        if any(part in marked for part in EXCLUDED_PARTS):
            continue
        if any(part in marked for part in TEST_FILE_MARKERS):
            continue
        yield rel


def _is_setting_reference(value):
    """
    True when the value is the NAME of a setting or environment variable rather
    than a secret — e.g. `api_key_setting = 'OPENROUTER_API_KEY'`. Requires the
    whole value to be an UPPER_SNAKE identifier that itself names a sensitive
    key, which no real credential looks like.
    """
    return bool(
        re.fullmatch(r'[A-Z][A-Z0-9_]*', value)
        and any(s in value for s in SENSITIVE_NAMES)
    )


def scan_line(line):
    """Return the offending variable name, or None. Never returns the value."""
    stripped = line.strip()
    if stripped.startswith('#') or _SAFE_LOOKUP.search(line):
        return None
    for match in _ASSIGN.finditer(line):
        name = match.group('name')
        if not any(s in name.upper() for s in SENSITIVE_NAMES):
            continue
        value = match.group('value')
        if _SAFE_VALUE.match(value) or _is_setting_reference(value):
            continue
        return name
    return None


class NoHardcodedSecretsTests(SimpleTestCase):

    def test_no_tracked_file_assigns_a_literal_secret(self):
        offences = []
        for rel in tracked_files():
            path = REPO_ROOT / rel
            if path.name == Path(__file__).name:
                continue          # this module names the patterns deliberately
            try:
                text = path.read_text(errors='ignore')
            except OSError:
                continue
            for number, line in enumerate(text.splitlines(), 1):
                name = scan_line(line)
                if name:
                    # File, line and variable name only — never the value.
                    offences.append(f'{rel}:{number} assigns a literal to {name}')
        self.assertEqual(
            offences, [],
            'hardcoded sensitive configuration found:\n  ' + '\n  '.join(offences))

    # ── the scanner itself ────────────────────────────────────────────────

    def test_detects_the_historical_defect_pattern(self):
        """
        The exact shape that caused this remediation: a module-level default
        password constant. An exact-name list would have missed it.
        """
        self.assertEqual(
            scan_line("_DEFAULT_PASSWORD = 'a-literal-password-value'"),
            '_DEFAULT_PASSWORD')

    def test_detects_a_hardcoded_password_assignment(self):
        self.assertEqual(
            scan_line("DEMO_PASSWORD = 'another-literal-value'"), 'DEMO_PASSWORD')

    def test_detects_a_hardcoded_admin_password(self):
        self.assertEqual(
            scan_line("ADMIN_PASSWORD = 'something-secret-here'"), 'ADMIN_PASSWORD')

    def test_detects_a_hardcoded_secret_key(self):
        self.assertEqual(
            scan_line("SECRET_KEY = 'kf83mfnq83hrf83hf8h38fh8'"), 'SECRET_KEY')

    def test_detects_a_hardcoded_yaml_api_key(self):
        self.assertEqual(scan_line('  API_KEY: "abc123def456"'), 'API_KEY')

    def test_accepts_an_environment_lookup(self):
        self.assertIsNone(
            scan_line("SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '')"))
        self.assertIsNone(
            scan_line("ADMIN_PASSWORD = os.getenv('BOOTSTRAP_ADMIN_PASSWORD')"))

    def test_accepts_an_empty_placeholder(self):
        self.assertIsNone(scan_line("API_KEY = ''"))
        self.assertIsNone(scan_line('  ACCESS_TOKEN: ""'))

    def test_accepts_render_secret_references(self):
        self.assertIsNone(scan_line('      - key: STRIPE_SECRET_KEY'))
        self.assertIsNone(scan_line('        sync: false'))

    def test_accepts_a_setting_name_reference(self):
        """`api_key_setting = 'OPENROUTER_API_KEY'` names a setting, not a secret."""
        self.assertIsNone(scan_line("api_key_setting = 'OPENROUTER_API_KEY'"))
        self.assertIsNone(scan_line("api_key_setting = 'AZURE_OPENAI_API_KEY'"))

    def test_still_rejects_a_lookalike_that_is_not_a_bare_name(self):
        self.assertEqual(
            scan_line("API_KEY = 'OPENROUTER_API_KEY_abc123'"), 'API_KEY')

    def test_accepts_documented_placeholders(self):
        self.assertIsNone(scan_line("API_KEY = 'your-api-key-here'"))
        self.assertIsNone(scan_line("PRIVATE_KEY = '<paste-key>'"))

    def test_ignores_comments(self):
        self.assertIsNone(scan_line("# ADMIN_PASSWORD = 'documented-example'"))

    def test_scanner_never_returns_a_value(self):
        """A failure message must name the variable, never the secret."""
        secret = 'this-exact-value-must-not-be-echoed'
        result = scan_line(f"ADMIN_PASSWORD = '{secret}'")
        self.assertEqual(result, 'ADMIN_PASSWORD')
        self.assertNotIn(secret, str(result))

    def test_the_historical_password_is_not_present_in_this_module(self):
        """This test file must not itself contain the compromised value."""
        source = Path(__file__).read_text()
        former = 'EcoIQ' + '2026!'          # reconstructed; never written literally
        self.assertNotIn(former, source)
