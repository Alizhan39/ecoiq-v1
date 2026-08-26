#!/usr/bin/env bash
#
# Install the approved third-party Claude Code skills into .claude/skills/.
#
# WHY THIS IS A SCRIPT AND NOT VENDORED CODE
# ------------------------------------------
# CLAUDE.md rule 14 and .gitignore keep `.claude/` out of git, with one
# deliberate exception: `.claude/skills/ecoiq-*/`, which is EcoIQ's own
# source. Third-party skill payloads stay machine-local. This script plus
# docs/ai-tooling/third-party-skills.lock.json is what makes that local
# state reproducible and reviewable: the SHAs are pinned, the copied
# subdirectories are explicit, and the diff shows up in a pull request.
#
# WHAT IT DOES NOT DO
# -------------------
#   * no global installs (no `npm i -g`, no `pip install --user`)
#   * no plugin marketplaces, no hooks, no SessionStart context injection
#   * nothing is executed from the upstream repositories — files are copied
#   * only the named subdirectories are copied, never a whole repository
#
# Every source, licence, and rejection reason:
#   docs/ai-tooling/THIRD_PARTY_SKILLS_AUDIT.md
#
# Usage:
#   bash scripts/ai-tooling/install-third-party-skills.sh          # install
#   bash scripts/ai-tooling/install-third-party-skills.sh --check  # verify only

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SKILLS_DIR="${REPO_ROOT}/.claude/skills"
WORK_DIR="$(mktemp -d)"
CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1

trap 'rm -rf "${WORK_DIR}"' EXIT

# repo|pinned-sha|source-subdir|destination-skill-name
PINS=(
  "anthropics/skills|3b3fad96af16a10759d930941b4520ba0c40edae|skills/frontend-design|frontend-design"
  "anthropics/skills|3b3fad96af16a10759d930941b4520ba0c40edae|skills/canvas-design|canvas-design"
  "anthropics/skills|3b3fad96af16a10759d930941b4520ba0c40edae|skills/algorithmic-art|algorithmic-art"
  "anthropics/skills|3b3fad96af16a10759d930941b4520ba0c40edae|skills/theme-factory|theme-factory"
  "anthropics/skills|3b3fad96af16a10759d930941b4520ba0c40edae|skills/web-artifacts-builder|web-artifacts-builder"
  "obra/superpowers|b36e0829c6d0140e93cfef2ca599b1b07d4a7797|skills/systematic-debugging|systematic-debugging"
  "kepano/obsidian-skills|a1dc48e68138490d522c04cbf5822214c6eb1202|skills/obsidian-markdown|obsidian-markdown"
  "muratcankoylan/Agent-Skills-for-Context-Engineering|6dbe1a1d868eab51a3bc9011b0f55e2891513e40|skills/context-optimization|context-optimization"
  "muratcankoylan/Agent-Skills-for-Context-Engineering|6dbe1a1d868eab51a3bc9011b0f55e2891513e40|skills/context-compression|context-compression"
)

# Files excluded after copy, with the reason. Upstream test fixtures and
# tooling that targets a stack EcoIQ does not use are dead weight in an
# always-listed skill directory.
declare -a PRUNE=(
  "systematic-debugging/find-polluter.sh"      # npm-only bisection; EcoIQ uses manage.py test
  "systematic-debugging/test-pressure-1.md"    # upstream eval fixture, not guidance
  "systematic-debugging/test-pressure-2.md"
  "systematic-debugging/test-pressure-3.md"
  "systematic-debugging/test-academic.md"
  "systematic-debugging/CREATION-LOG.md"
)

fetch_repo() {
  local repo="$1" sha="$2" dest="${WORK_DIR}/$(echo "$1" | tr '/' '_')"
  [ -d "$dest" ] && return 0
  echo "  fetching ${repo}@${sha:0:12}"
  git clone --quiet --filter=blob:none --no-checkout "https://github.com/${repo}.git" "$dest"
  git -C "$dest" fetch --quiet --depth 1 origin "$sha"
  git -C "$dest" checkout --quiet "$sha"
  local actual
  actual="$(git -C "$dest" rev-parse HEAD)"
  if [ "$actual" != "$sha" ]; then
    echo "  ERROR: ${repo} resolved to ${actual}, expected ${sha}" >&2
    exit 1
  fi
}

write_provenance() {
  local name="$1" repo="$2" sha="$3" subdir="$4"
  cat > "${SKILLS_DIR}/${name}/PROVENANCE.md" <<PROV
# Provenance — ${name}

Third-party skill vendored into EcoIQ. **Not EcoIQ source.** Upstream owns
the content; EcoIQ owns only the decision to install it and the restrictions
recorded in the audit.

| | |
|---|---|
| Upstream | https://github.com/${repo} |
| Path in upstream | \`${subdir}/\` |
| Pinned commit | \`${sha}\` |
| Installed by | \`scripts/ai-tooling/install-third-party-skills.sh\` |
| Audit + restrictions | \`docs/ai-tooling/THIRD_PARTY_SKILLS_AUDIT.md\` |
| EcoIQ usage boundaries | \`docs/ai-tooling/SECURITY_BOUNDARIES.md\` |

Upstream licence text is preserved in this directory where upstream shipped
one. Do not edit the upstream files in place — re-pin the SHA in the
installer instead, so the change is visible in review.
PROV
}

echo "Installing approved third-party skills into ${SKILLS_DIR}"
mkdir -p "${SKILLS_DIR}"

for pin in "${PINS[@]}"; do
  IFS='|' read -r repo sha subdir name <<< "$pin"
  if [ "$CHECK_ONLY" = "1" ]; then
    if [ -f "${SKILLS_DIR}/${name}/SKILL.md" ]; then
      echo "  ok      ${name}"
    else
      echo "  MISSING ${name}"
    fi
    continue
  fi
  fetch_repo "$repo" "$sha"
  src="${WORK_DIR}/$(echo "$repo" | tr '/' '_')/${subdir}"
  if [ ! -d "$src" ]; then
    echo "  ERROR: ${subdir} not present in ${repo}@${sha}" >&2
    exit 1
  fi
  rm -rf "${SKILLS_DIR:?}/${name}"
  mkdir -p "${SKILLS_DIR}/${name}"
  cp -R "${src}/." "${SKILLS_DIR}/${name}/"
  write_provenance "$name" "$repo" "$sha" "$subdir"
  echo "  installed ${name}"
done

if [ "$CHECK_ONLY" = "1" ]; then
  exit 0
fi

# ---------------------------------------------------------------------------
# Explicit reference rewrites.
#
# systematic-debugging ships inside the `superpowers` plugin and points at two
# sibling skills in that plugin (`superpowers:test-driven-development`,
# `superpowers:verification-before-completion`). EcoIQ installs the skill
# directory ONLY, not the plugin, so those references resolve to nothing —
# a dangling instruction the agent would follow confidently. They are
# redirected to the EcoIQ skill that actually owns each job.
#
# Rewrites are done here, in the installer, so re-running against a new
# upstream SHA reapplies them and the mapping stays visible in review.
# ---------------------------------------------------------------------------
rewrite() {
  local file="$1" from="$2" to="$3"
  [ -f "$file" ] || return 0
  grep -q "$from" "$file" || return 0
  perl -pi -e "s/\Q${from}\E/${to}/g" "$file"
  echo "  rewrote   $(basename "$(dirname "$file")")/$(basename "$file"): ${from} -> ${to}"
}

SD="${SKILLS_DIR}/systematic-debugging/SKILL.md"
rewrite "$SD" "superpowers:test-driven-development" "ecoiq-release-gate"
rewrite "$SD" "superpowers:verification-before-completion" "ecoiq-release-gate"

for rel in "${PRUNE[@]}"; do
  if [ -e "${SKILLS_DIR}/${rel}" ]; then
    rm -f "${SKILLS_DIR:?}/${rel}"
    echo "  pruned    ${rel}"
  fi
done

echo
echo "Done. Restrictions are NOT enforced by this script — read"
echo "docs/ai-tooling/THIRD_PARTY_SKILLS_AUDIT.md before using any of them."
