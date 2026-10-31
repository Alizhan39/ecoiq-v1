#!/usr/bin/env bash
#
# Start the Excel MCP server inside EcoIQ's security boundary.
#
# READ THIS BEFORE CHANGING ANY FLAG BELOW
# ----------------------------------------
# Two settings in this file are load-bearing. Both were found by reading the
# upstream source, not the upstream README. Weakening either one turns this
# into an unauthenticated read/write filesystem API.
#
#   1. TRANSPORT MUST BE streamable-http, NEVER stdio.
#      In stdio mode the server sets EXCEL_FILES_PATH to None, and
#      get_excel_path() then *requires an absolute path and returns it
#      unchanged* (src/excel_mcp/server.py, get_excel_path). There is no
#      confinement at all: .env, db.sqlite3, ~/.ssh — all readable and
#      writable. Only the HTTP/SSE transports assign EXCEL_FILES_PATH and
#      run the realpath + commonpath containment check.
#
#   2. FASTMCP_HOST MUST BE 127.0.0.1.
#      Upstream defaults to 0.0.0.0 (server.py line ~70) and ships no
#      authentication. On any shared network that publishes this server to
#      every host on the LAN.
#
# The workspace is a dedicated directory that holds nothing but spreadsheets
# the user put there on purpose. It is NOT the repository, NOT $HOME, and NOT
# production storage. See docs/ai-tooling/SECURITY_BOUNDARIES.md.
#
# Usage:
#   bash scripts/ai-tooling/start-excel-mcp.sh
#   bash scripts/ai-tooling/start-excel-mcp.sh --check   # verify, do not serve

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# --- the boundary -----------------------------------------------------------
EXCEL_WORKSPACE="${REPO_ROOT}/data/mcp/excel"
EXCEL_MCP_VERSION="0.1.8"
export EXCEL_FILES_PATH="${EXCEL_WORKSPACE}"
export FASTMCP_HOST="127.0.0.1"
export FASTMCP_PORT="${FASTMCP_PORT:-8017}"
# ----------------------------------------------------------------------------

VENV="${REPO_ROOT}/.venv-mcp"
PY="${VENV}/bin/python"

mkdir -p "${EXCEL_WORKSPACE}"

if [ ! -x "${PY}" ]; then
  echo "Creating isolated MCP virtualenv at .venv-mcp/ (separate from the Django .venv)"
  python3 -m venv "${VENV}"
  "${VENV}/bin/pip" install --quiet --upgrade pip
fi

if ! "${PY}" -c "import excel_mcp" 2>/dev/null; then
  echo "Installing excel-mcp-server==${EXCEL_MCP_VERSION} (pinned)"
  "${VENV}/bin/pip" install --quiet "excel-mcp-server==${EXCEL_MCP_VERSION}"
fi

INSTALLED="$("${PY}" -c "import importlib.metadata as m; print(m.version('excel-mcp-server'))")"
if [ "${INSTALLED}" != "${EXCEL_MCP_VERSION}" ]; then
  echo "ERROR: excel-mcp-server is ${INSTALLED}, expected pinned ${EXCEL_MCP_VERSION}" >&2
  exit 1
fi

echo "excel-mcp-server ${INSTALLED}"
echo "  transport : streamable-http  (stdio is unconfined and is never used)"
echo "  bind      : ${FASTMCP_HOST}:${FASTMCP_PORT}  (loopback only)"
echo "  workspace : ${EXCEL_FILES_PATH}"

if [ "${1:-}" = "--check" ]; then
  echo "--check: configuration verified, not serving."
  exit 0
fi

echo
echo "Claude Code connects to http://127.0.0.1:${FASTMCP_PORT}/mcp — see"
echo "docs/ai-tooling/MCP_SETUP.md. Ctrl-C to stop."
exec "${PY}" -m excel_mcp streamable-http
