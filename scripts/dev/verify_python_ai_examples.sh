#!/usr/bin/env bash
# Read-only checks: no deploy, migrate, credentials, data transfer or cloud calls.
# Usage: bash scripts/dev/verify_python_ai_examples.sh [--django|--full]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
RUN_DJANGO=0
RUN_FULL=0
for arg in "$@"; do
  case "$arg" in
    --django) RUN_DJANGO=1 ;;
    --full) RUN_DJANGO=1; RUN_FULL=1 ;;
    -h|--help)
      echo "Usage: bash scripts/dev/verify_python_ai_examples.sh [--django|--full]"
      exit 0 ;;
    *) printf "Unknown argument: %s\\n" "$arg" >&2; exit 2 ;;
  esac
done

PYTHON_BIN="${PYTHON_BIN:-python}"
"$PYTHON_BIN" -m compileall -q examples/python_ai_devops
"$PYTHON_BIN" -m unittest examples.python_ai_devops.test_examples
if command -v ruff >/dev/null 2>&1; then
  ruff check examples/python_ai_devops
fi
if [[ "$RUN_DJANGO" == "1" ]]; then
  "$PYTHON_BIN" manage.py check
  "$PYTHON_BIN" manage.py makemigrations --check --dry-run
  "$PYTHON_BIN" manage.py test api.tests_os_pilot_journey api.tests_v2_decision_islah api.tests_v2_process_analyses core.tests_process_workspace --noinput
fi
if [[ "$RUN_FULL" == "1" ]]; then
  "$PYTHON_BIN" manage.py test --noinput
fi
