# MCP setup

Current MCP configuration for this repository, and the exact steps to enable
the one server that is configured but not yet active.

Format verified against the installed **Claude Code 2.1.209** (`claude mcp
--help`): project servers live in `.mcp.json` at the repository root; stdio
servers use `command` + `args`, HTTP servers use `type` + `url`.

## Active

`.mcp.json` — unchanged by this branch:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  }
}
```

Verified this session: `claude mcp list` → `playwright: ✔ Connected`. The
approval that was pending in the previous tooling pass has since been granted.

## Excel MCP — configured, not yet active

**Status: MANUAL AUTHORIZATION REQUIRED.** Not added to `.mcp.json` on
purpose. The safe transport is `streamable-http`, which Claude Code connects
to but does not start; an entry pointing at a server that is not running
fails its health check on every session start. Start the server, then add the
entry.

### Why not stdio, which would auto-start

Because stdio has no filesystem confinement. With `EXCEL_FILES_PATH` unset —
which is exactly what stdio mode does — `get_excel_path()` requires an
absolute path and returns it unchanged. `.env`, `db.sqlite3` and `~/.ssh`
would all be readable and writable. Full detail:
[THIRD_PARTY_SKILLS_AUDIT.md](THIRD_PARTY_SKILLS_AUDIT.md).

### Step 1 — start the server

```bash
bash scripts/ai-tooling/start-excel-mcp.sh
```

First run creates `.venv-mcp/` (gitignored, separate from the Django `.venv`)
and installs `excel-mcp-server==0.1.8`, pinned. The script sets, and you
should not change:

| Variable | Value | Why |
|---|---|---|
| `EXCEL_FILES_PATH` | `data/mcp/excel` | The only directory the server can reach |
| `FASTMCP_HOST` | `127.0.0.1` | Upstream defaults to `0.0.0.0`, unauthenticated |
| `FASTMCP_PORT` | `8017` | Override only to resolve a port clash |
| transport | `streamable-http` | The only mode that enforces the path boundary |

Verify configuration without serving:

```bash
bash scripts/ai-tooling/start-excel-mcp.sh --check
```

### Step 2 — add the client entry

Add to `.mcp.json` (this is the real config, not a placeholder — it contains
no secret):

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    },
    "excel": {
      "type": "http",
      "url": "http://127.0.0.1:8017/mcp"
    }
  }
}
```

Or, equivalently:

```bash
claude mcp add --transport http excel http://127.0.0.1:8017/mcp
```

Claude Code shows a one-time approval prompt for a new `.mcp.json` server.
That prompt is a connection approval, not a credential.

### Step 3 — verify

```bash
claude mcp list
```

Expect `excel: … ✔ Connected`. Then prove the boundary still holds:

```bash
.venv-mcp/bin/python scripts/ai-tooling/verify-excel-mcp-boundary.py
```

Expect `15 passed, 0 failed`. Run this again after any upstream version bump —
it is the check that would catch upstream loosening the confinement.

Confirm the bind is loopback-only:

```bash
lsof -nP -iTCP:8017 -sTCP:LISTEN
```

The `NAME` column must read `127.0.0.1:8017`. If it reads `*:8017`, stop the
server — `FASTMCP_HOST` did not take effect and the API is on the LAN.

### Step 4 — stop it when done

```bash
pkill -f "excel_mcp streamable-http"
```

It is a local tool, not a service. Leave it running only while in use.

## No secrets in any of this

Neither server takes an API key, token or credential. Nothing in `.mcp.json`
is sensitive. If a future MCP server does need a secret, it goes in an
ignored local env file or the platform secret manager — never in `.mcp.json`,
which is committed.

## Example placeholder — a hypothetical server that needs a key

For reference only. Not configured, not installed.

```json
{
  "mcpServers": {
    "example-service": {
      "command": "some-mcp-server",
      "args": ["stdio"],
      "env": {
        "EXAMPLE_API_KEY": "${EXAMPLE_API_KEY}"
      }
    }
  }
}
```

The value stays an environment-variable reference. Never paste a real key.
