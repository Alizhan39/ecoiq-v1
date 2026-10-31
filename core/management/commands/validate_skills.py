"""
Management command: validate_skills

Validates the EcoIQ Engineering OS skills under `.claude/skills/ecoiq-*/`.

Why this exists: a skill is an instruction the agent will follow confidently.
A stale one — pointing at a deleted module, or duplicating a trigger another
skill already owns — is worse than no skill at all, because it is wrong with
authority. This command is the gate that keeps them honest, and it runs in CI.

What it checks:
  * SKILL.md exists, is readable, and has YAML frontmatter delimited by ---
  * frontmatter has exactly the `name` and `description` keys
  * `name` matches the directory name and the ecoiq-* convention
  * `description` is non-trivial, under the length budget, and states triggers
  * no two skills claim the same trigger phrase (routing collisions)
  * every repo-relative markdown link resolves to a real path
  * the router skill's route table mentions every other skill

Deliberately dependency-free: no PyYAML (not in requirements.txt), so the
frontmatter parser here handles only the flat `key: value` shape the skill
format actually uses, and reports anything else as an error rather than
silently accepting it.

Usage:
    python manage.py validate_skills
    python manage.py validate_skills --strict   # exit 1 on any error

Paired skill: .claude/skills/ecoiq-skill-creator/SKILL.md
"""
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

SKILL_DIR_PREFIX = 'ecoiq-'
ROUTER_SKILL = 'ecoiq-engineering-os'
MAX_DESCRIPTION_CHARS = 500
MIN_DESCRIPTION_CHARS = 60
FRONTMATTER_KEYS = {'name', 'description'}

MARKDOWN_LINK_RE = re.compile(r'\[[^\]]*\]\(([^)]+)\)')
FRONTMATTER_LINE_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$')

# Trigger phrases that would make two skills compete for the same task. Each
# is checked across every skill's description; two owners is a routing bug.
CONTESTED_TRIGGERS = (
    'evidence chain',
    'impact claim',
    'regulatory',
    'security review',
    'release gate',
    'brand',
    'seo',
    'prototype',
    'remotion',
    'skill',
)


class Command(BaseCommand):
    help = 'Validate the EcoIQ Engineering OS skills in .claude/skills/ecoiq-*/.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--strict', action='store_true',
            help='Exit with status 1 if any error is reported.',
        )

    def handle(self, *args, **options):
        root = skills_root()
        if not root.exists():
            self.stdout.write(self.style.WARNING(f'No skills directory at {root} — nothing to validate.'))
            return

        skills, errors = load_skills(root)

        for skill in sorted(skills, key=lambda s: s['name']):
            self.stdout.write(self.style.SUCCESS(f'  ok  {skill["name"]}'))

        for error in errors:
            self.stdout.write(self.style.ERROR(f' err  {error}'))

        self.stdout.write('')
        self.stdout.write(f'{len(skills)} skill(s) validated, {len(errors)} error(s)')

        if errors and options['strict']:
            raise SystemExit(1)


def skills_root():
    return Path(settings.BASE_DIR) / '.claude' / 'skills'


def load_skills(root):
    """Return (skills, errors). Importable so tests assert without shelling out."""
    skills = []
    errors = []

    directories = sorted(
        p for p in root.iterdir()
        if p.is_dir() and p.name.startswith(SKILL_DIR_PREFIX)
    )

    if not directories:
        return skills, ['no ecoiq-* skill directories found']

    for directory in directories:
        skill_file = directory / 'SKILL.md'
        if not skill_file.exists():
            errors.append(f'{directory.name}: no SKILL.md')
            continue

        text = skill_file.read_text(encoding='utf-8')
        frontmatter, body, parse_errors = parse_frontmatter(text)
        errors.extend(f'{directory.name}: {e}' for e in parse_errors)
        if frontmatter is None:
            continue

        errors.extend(
            f'{directory.name}: {e}'
            for e in check_frontmatter(frontmatter, directory.name)
        )
        errors.extend(
            f'{directory.name}: {e}'
            for e in check_links(body, skill_file)
        )

        skills.append({
            'name': frontmatter.get('name', directory.name),
            'description': frontmatter.get('description', ''),
            'directory': directory,
            'body': body,
        })

    errors.extend(check_trigger_collisions(skills))
    errors.extend(check_router_coverage(skills))
    return skills, errors


def parse_frontmatter(text):
    """Parse the flat `key: value` frontmatter block. Returns (dict, body, errors)."""
    if not text.startswith('---\n'):
        return None, '', ['missing YAML frontmatter (file must start with ---)']

    end = text.find('\n---\n', 4)
    if end == -1:
        return None, '', ['frontmatter block is not closed with ---']

    block = text[4:end]
    body = text[end + len('\n---\n'):]

    data = {}
    errors = []
    for line in block.splitlines():
        if not line.strip():
            continue
        match = FRONTMATTER_LINE_RE.match(line)
        if not match:
            errors.append(f'frontmatter line is not a simple "key: value" pair: {line[:60]!r}')
            continue
        key, value = match.group(1), match.group(2).strip()
        if key in data:
            errors.append(f'duplicate frontmatter key "{key}"')
        data[key] = value

    return data, body, errors


def check_frontmatter(frontmatter, directory_name):
    errors = []

    extra = set(frontmatter) - FRONTMATTER_KEYS
    missing = FRONTMATTER_KEYS - set(frontmatter)
    for key in sorted(missing):
        errors.append(f'frontmatter is missing "{key}"')
    for key in sorted(extra):
        errors.append(f'unexpected frontmatter key "{key}" (only name and description are used)')

    name = frontmatter.get('name', '')
    if name and name != directory_name:
        errors.append(f'frontmatter name "{name}" does not match directory "{directory_name}"')
    if name and not name.startswith(SKILL_DIR_PREFIX):
        errors.append(f'name "{name}" must start with "{SKILL_DIR_PREFIX}"')

    description = frontmatter.get('description', '')
    if description:
        if len(description) > MAX_DESCRIPTION_CHARS:
            errors.append(
                f'description is {len(description)} chars, over the '
                f'{MAX_DESCRIPTION_CHARS} budget — it is read on every routing decision'
            )
        if len(description) < MIN_DESCRIPTION_CHARS:
            errors.append(
                f'description is only {len(description)} chars — too vague to route on'
            )
        if 'use when' not in description.lower():
            errors.append('description has no "Use when" clause stating its triggers')

    return errors


def check_links(body, skill_file):
    """Every repo-relative link in a skill must resolve. A skill pointing at a
    deleted file is exactly the stale-instruction failure this guards against."""
    errors = []
    for target in MARKDOWN_LINK_RE.findall(body):
        target = target.split('#', 1)[0].strip()
        if not target or target.startswith(('http://', 'https://', 'mailto:')):
            continue
        resolved = (skill_file.parent / target).resolve()
        if not resolved.exists():
            errors.append(f'link target does not exist: {target}')
    return errors


def check_trigger_collisions(skills):
    """Two skills owning the same trigger phrase makes routing ambiguous.

    The router is exempt: naming every domain is precisely its job, so it
    collides with everything by design. Excluding it here is what makes the
    check meaningful for the skills that actually compete with each other.
    """
    errors = []
    candidates = [s for s in skills if s['name'] != ROUTER_SKILL]
    for trigger in CONTESTED_TRIGGERS:
        owners = [
            s['name'] for s in candidates
            if trigger in s['description'].lower().split('not for')[0]
        ]
        if len(owners) > 1:
            errors.append(
                f'trigger "{trigger}" is claimed by {len(owners)} skills '
                f'({", ".join(sorted(owners))}) — routing is ambiguous'
            )
    return errors


def check_router_coverage(skills):
    """The router must list every skill, or a skill is unreachable by routing."""
    router = next((s for s in skills if s['name'] == ROUTER_SKILL), None)
    if router is None:
        return [f'{ROUTER_SKILL}: router skill is missing']

    errors = []
    for skill in skills:
        if skill['name'] == ROUTER_SKILL:
            continue
        if skill['name'] not in router['body']:
            errors.append(
                f'{ROUTER_SKILL}: route table does not mention "{skill["name"]}"'
            )
    return errors
