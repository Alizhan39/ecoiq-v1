"""
Tests for the third-party AI tooling layer (docs/ai-tooling/).

The threat this guards against is drift, in three forms:

  1. The installer and the provenance lockfile disagreeing about which commit
     is installed — at which point the audit describes code nobody is running.
  2. An installed third-party skill carrying instruction-override text. These
     are files from untrusted upstreams that Claude reads as instructions;
     re-pinning to a newer SHA could introduce one silently.
  3. The Excel MCP server being reconfigured onto its unconfined stdio
     transport, which would give it read/write access to the whole filesystem.

Skill payloads are gitignored (CLAUDE.md rule 14), so the tests that need
them skip when they are absent — as in CI. The tests that check committed
files always run.

Nothing here touches the network, the database, or any external service.
"""
import json
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

BASE = Path(settings.BASE_DIR)
LOCKFILE = BASE / 'docs' / 'ai-tooling' / 'third-party-skills.lock.json'
INSTALLER = BASE / 'scripts' / 'ai-tooling' / 'install-third-party-skills.sh'
SKILLS_DIR = BASE / '.claude' / 'skills'
MCP_CONFIG = BASE / '.mcp.json'

# Patterns that would mean an upstream file is trying to redirect the agent
# rather than inform it. Deliberately narrow: broad patterns match ordinary
# prose about security and train people to ignore the failure.
INJECTION_PATTERNS = (
    r'ignore\s+(all\s+)?previous\s+instructions',
    r'disregard\s+(all\s+)?(previous|prior)\s+instructions',
    r'override\s+the\s+system\s+prompt',
    r'you\s+are\s+now\s+in\s+developer\s+mode',
    r'curl[^\n]*\|\s*(ba)?sh',
    r'cat\s+[^\n]*\.env',
    r'~/\.ssh/id_',
)

# Pinned SHAs are 40-hex. Anything shorter in the installer is a typo that
# would silently resolve to a different commit.
PIN_RE = re.compile(r'^\s*"([^|"]+)\|([0-9a-f]{40})\|([^|]+)\|([^|"]+)"\s*$', re.M)


def load_lockfile():
    return json.loads(LOCKFILE.read_text(encoding='utf-8'))


class LockfileTests(SimpleTestCase):
    """The lockfile is the audit's machine-readable half. It must be true."""

    def test_lockfile_exists_and_parses(self):
        self.assertTrue(LOCKFILE.exists(), f'{LOCKFILE} is missing')
        data = load_lockfile()
        self.assertTrue(data['skills'], 'lockfile records no skills')

    def test_every_locked_skill_has_a_pinned_40_hex_commit(self):
        for entry in load_lockfile()['skills']:
            with self.subTest(skill=entry['name']):
                self.assertRegex(
                    entry['commit'], r'^[0-9a-f]{40}$',
                    'a short or missing SHA can resolve to a different commit',
                )

    def test_every_locked_skill_declares_licence_and_verdict(self):
        allowed = {'APPROVED', 'APPROVED WITH RESTRICTIONS'}
        for entry in load_lockfile()['skills']:
            with self.subTest(skill=entry['name']):
                self.assertTrue(entry.get('license'), 'no licence recorded')
                self.assertIn(
                    entry.get('verdict'), allowed,
                    'an installed skill must carry an approving verdict',
                )

    def test_restricted_skills_actually_state_their_restrictions(self):
        for entry in load_lockfile()['skills']:
            if entry.get('verdict') == 'APPROVED WITH RESTRICTIONS':
                with self.subTest(skill=entry['name']):
                    self.assertTrue(
                        entry.get('restrictions'),
                        'marked restricted but lists no restriction',
                    )

    def test_rejected_components_each_carry_a_reason(self):
        rejected = load_lockfile()['rejected']
        self.assertTrue(rejected, 'no rejections recorded — the audit rejected six')
        for entry in rejected:
            with self.subTest(component=entry['name']):
                self.assertGreater(
                    len(entry.get('reason', '')), 40,
                    'a rejection without a substantive reason cannot be reviewed',
                )


class InstallerAgreesWithLockfileTests(SimpleTestCase):
    """Installer and lockfile must name the same commits.

    If they diverge, the audit documents one thing and the installer produces
    another — the exact failure that makes a provenance record worthless.
    """

    def installer_pins(self):
        return {
            (name, sha)
            for repo, sha, subdir, name in PIN_RE.findall(INSTALLER.read_text(encoding='utf-8'))
        }

    def test_installer_exists(self):
        self.assertTrue(INSTALLER.exists(), f'{INSTALLER} is missing')

    def test_installer_and_lockfile_pin_identical_commits(self):
        installer = self.installer_pins()
        locked = {(e['name'], e['commit']) for e in load_lockfile()['skills']}
        self.assertEqual(
            installer, locked,
            'installer and third-party-skills.lock.json disagree; '
            'update both together',
        )

    def test_installer_performs_no_global_installs(self):
        """Applies to executable lines only.

        The installer's header comment enumerates what it does *not* do, so a
        naive whole-file scan matches its own documentation.
        """
        code = '\n'.join(
            line for line in INSTALLER.read_text(encoding='utf-8').splitlines()
            if not line.lstrip().startswith('#')
        )
        for forbidden in ('npm install -g', 'npm i -g', 'pip install --user', 'sudo '):
            with self.subTest(pattern=forbidden):
                self.assertNotIn(
                    forbidden, code,
                    'installs must stay project-local',
                )


class McpConfigurationTests(SimpleTestCase):
    """The Excel MCP boundary depends entirely on transport choice."""

    def test_mcp_config_parses(self):
        self.assertTrue(MCP_CONFIG.exists(), '.mcp.json is missing')
        self.assertIn('mcpServers', json.loads(MCP_CONFIG.read_text(encoding='utf-8')))

    def test_excel_mcp_is_never_configured_over_stdio(self):
        """stdio gives the server the whole filesystem.

        With EXCEL_FILES_PATH unset — which is what stdio mode does —
        get_excel_path() accepts any absolute path and returns it unchanged.
        A `command`-style entry for excel means someone moved it to stdio.
        """
        servers = json.loads(MCP_CONFIG.read_text(encoding='utf-8'))['mcpServers']
        for name, config in servers.items():
            if 'excel' not in name.lower():
                continue
            with self.subTest(server=name):
                self.assertNotIn(
                    'command', config,
                    'Excel MCP must use the http transport, never stdio — '
                    'see docs/ai-tooling/SECURITY_BOUNDARIES.md',
                )
                self.assertTrue(
                    config.get('url', '').startswith(('http://127.0.0.1', 'http://localhost')),
                    'Excel MCP must be reached over loopback only',
                )

    def test_launcher_pins_the_two_load_bearing_settings(self):
        launcher = BASE / 'scripts' / 'ai-tooling' / 'start-excel-mcp.sh'
        self.assertTrue(launcher.exists(), f'{launcher} is missing')
        text = launcher.read_text(encoding='utf-8')
        self.assertIn('FASTMCP_HOST="127.0.0.1"', text,
                      'upstream defaults to 0.0.0.0 with no authentication')
        self.assertIn('streamable-http', text)
        self.assertNotIn('run_stdio', text)


class InstalledSkillTests(SimpleTestCase):
    """Checks against the installed payloads.

    Payloads are gitignored, so these skip in CI and on a fresh clone. They
    are the checks that matter after someone re-pins to a newer upstream SHA.
    """

    def installed(self):
        return [
            (e['name'], SKILLS_DIR / e['name'])
            for e in load_lockfile()['skills']
            if (SKILLS_DIR / e['name'] / 'SKILL.md').exists()
        ]

    def test_installed_skills_carry_provenance(self):
        installed = self.installed()
        if not installed:
            self.skipTest('third-party skills not installed (payloads are gitignored)')
        for name, path in installed:
            with self.subTest(skill=name):
                provenance = path / 'PROVENANCE.md'
                self.assertTrue(
                    provenance.exists(),
                    'installed without provenance — run the installer',
                )
                self.assertIn('https://github.com/', provenance.read_text(encoding='utf-8'))

    def test_installed_skills_contain_no_instruction_override_text(self):
        installed = self.installed()
        if not installed:
            self.skipTest('third-party skills not installed (payloads are gitignored)')
        for name, path in installed:
            for markdown in path.rglob('*.md'):
                if markdown.name == 'PROVENANCE.md':
                    continue
                text = markdown.read_text(encoding='utf-8', errors='replace')
                for pattern in INJECTION_PATTERNS:
                    with self.subTest(skill=name, file=markdown.name, pattern=pattern):
                        self.assertIsNone(
                            re.search(pattern, text, re.I),
                            f'{markdown} matches an instruction-override pattern; '
                            're-audit before keeping this pin',
                        )

    def test_systematic_debugging_has_no_dangling_plugin_references(self):
        """It ships inside a plugin EcoIQ does not install.

        Upstream points at sibling skills that do not exist here. The
        installer rewrites them; a re-pin that skipped the rewrite would
        leave the agent following a reference to nothing.
        """
        skill = SKILLS_DIR / 'systematic-debugging' / 'SKILL.md'
        if not skill.exists():
            self.skipTest('systematic-debugging not installed')
        self.assertNotIn(
            'superpowers:', skill.read_text(encoding='utf-8'),
            'dangling superpowers: reference — re-run the installer',
        )
