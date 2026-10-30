"""Read-only Stage 8 preflight. Must run before provisioning any pilot server.

Usage: DJANGO_SETTINGS_MODULE=ecoiq.settings_pilot python scripts/pilot/preflight.py
Does not print DB/credentials, perform migrations or create Render resources.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ecoiq.settings_pilot")


def main() -> int:
    try:
        import django
        django.setup()
        from django.conf import settings
        from ecoiq_os.pilot_security import assess_pilot_preflight
        report = assess_pilot_preflight(settings, os.environ)
    except Exception:
        # Avoid echoing exceptions from URL/password-bearing Django settings.
        print(json.dumps({
            "ready_for_synthetic_staging_preflight": False,
            "error": "Pilot settings could not pass safe initialisation.",
        }))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready_for_synthetic_staging_preflight"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
