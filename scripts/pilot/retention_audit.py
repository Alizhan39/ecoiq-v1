"""Read-only retention counts. No plaintext content and no delete command."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ecoiq.settings_pilot")


def main():
    try:
        import django
        django.setup()
        from ecoiq_os.pilot_retention import retention_inventory
        result = retention_inventory()
    except Exception:
        print(json.dumps({"error": "Isolated pilot environment not verified.", "delete_performed": False}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
