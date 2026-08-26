---
name: ecoiq-skill-creator
description: Create, change, or retire an EcoIQ project skill under .claude/skills/ecoiq-*/. Use when asked to add a new skill, when an existing skill's triggers overlap or misfire, or when a skill has gone stale against the code it describes. Covers the required frontmatter, trigger discipline, provenance, and the validator that gates it. Not for third-party or user-level skills, which are not part of this repository.
---

# Creating an EcoIQ skill

## First: do not create one

Most "we need a skill" requests are answered by an existing one, a paragraph
in an existing skill, or a doc. A new skill earns its place only if it has a
**trigger no existing skill covers** and would otherwise be re-explained in
every session. Check the route table in
[`ecoiq-engineering-os`](../ecoiq-engineering-os/SKILL.md) before adding.

Fourteen skills is already near the useful ceiling. Adding a fifteenth that
overlaps an existing trigger makes routing worse for every task, not better.

## Required shape

```
.claude/skills/ecoiq-<name>/SKILL.md
```

Frontmatter — exactly two keys, `name` and `description`:

```yaml
---
name: ecoiq-<name>          # must equal the directory name
description: <what it does>. Use when <specific triggers>. Not for <the near-miss it should not catch>.
---
```

The `description` is the only thing read when deciding whether to load the
skill, so it carries the whole routing decision. Three parts, in order:

1. **What** — concrete nouns from this codebase, not abstractions.
2. **Use when** — the situations that should fire it. Name real things:
   models, URLs, file types, page kinds.
3. **Not for** — the nearest thing that should *not* fire it. This is the
   part people skip, and it is the part that prevents two skills fighting.

Under 500 characters. If it needs more, the skill is doing two jobs.

## Body rules

- **Link, never restate.** Domain rules live in the code and in `docs/`.
  A skill that copies a colour value, a model field, or a regulation will be
  wrong within a month, and confidently wrong. Link to the file and say what
  to look for.
- **Cite real paths.** `validate_skills` fails the build if a repo-relative
  path referenced in a skill no longer exists.
- **State what is not true.** Where the codebase does not yet do something
  the product vocabulary implies, say so — see `ecoiq-khalifah-loop`, which
  records that the twelve loop stages are not implemented under those names.
  A skill that flatters the architecture is worse than no skill.
- **End with "Done when".** Concrete, checkable conditions.
- Keep it under roughly 150 lines. Progressive disclosure means the body is
  read *after* the routing decision — long bodies cost every invocation.

## Optional extras

Scripts, references, and assets go in the skill directory beside `SKILL.md`.
Prefer a **Django management command** over a loose script: it is importable,
testable by the normal suite, and runs in CI. `ecoiq-seo-audit` →
`core/management/commands/seo_audit.py` is the pattern to copy.

Any script must be inspectable, dependency-free beyond `requirements.txt`,
and must not make a network call unless that is its entire stated purpose.

## Provenance

If a skill adapts a third-party pattern, add a row to
[`docs/THIRD-PARTY-INTEGRATIONS.json`](../../../docs/THIRD-PARTY-INTEGRATIONS.json)
recording source URL, pinned version or commit, licence, what was adapted,
and the decision (`adopt` / `adapt` / `isolate` / `defer` / `reject`).
Vendoring a whole repository is not the pattern here; nothing in this OS was
installed from a candidate repository's own installer.

## Validate

```bash
.venv/bin/python manage.py validate_skills          # human-readable
.venv/bin/python manage.py validate_skills --strict # exit 1 on error (CI)
```

It checks frontmatter presence and shape, `name` matching the directory,
description length and the "Use when" clause, trigger-word collisions between
skills, and that every repo-relative link resolves. Covered by
`core/tests_engineering_os.py`.

## Retiring a skill

Delete the directory and remove its row from the route table in
`ecoiq-engineering-os`. Leaving a stale skill in place is the failure mode
this whole layer exists to prevent — a confident, out-of-date instruction is
worse than an absent one.

## Done when

- `validate_skills --strict` passes.
- The route table lists the new skill with a "Not" column entry.
- No existing skill's triggers now overlap it.
- Provenance recorded if anything external was adapted.
