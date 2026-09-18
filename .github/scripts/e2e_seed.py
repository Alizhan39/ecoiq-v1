"""
Create the CI-only fixture user for the mobile<->Django contract E2E test.

Deliberately NOT a Django management command. A command shipped in the
application is a permanent, callable code path in production; this is a script
that only exists on the CI runner's checkout and is invoked explicitly by the
mobile-backend-e2e job:

    python manage.py shell < .github/scripts/e2e_seed.py

The credentials come from the environment. The workflow generates them per run
with `openssl rand`, so nothing is hardcoded, nothing is reusable, and the
account dies with the ephemeral runner database.

Refuses to run against anything that is not an obviously disposable CI
database, so it cannot be pointed at real data by accident.
"""
import os
import sys

from django.conf import settings
from django.contrib.auth import get_user_model

username = os.environ.get('E2E_USERNAME', '')
password = os.environ.get('E2E_PASSWORD', '')
email = os.environ.get('E2E_EMAIL', '')

if not username or not password:
    sys.exit('E2E_USERNAME and E2E_PASSWORD must be set by the CI job.')

# Guard: only ever touch a throwaway CI database.
db_name = str(settings.DATABASES['default'].get('NAME', ''))
if 'e2e' not in db_name:
    sys.exit(
        f'refusing to seed: database {db_name!r} is not an e2e fixture '
        f'database. This script must never run against real data.'
    )

User = get_user_model()
user, created = User.objects.get_or_create(
    username=username,
    defaults={'email': email, 'is_staff': False, 'is_superuser': False},
)
# Always set the password explicitly: the account is generated fresh each run,
# and a stale hash would make the contract test fail for the wrong reason.
user.set_password(password)
user.is_active = True
# Never privileged. The contract under test is an ordinary app user's.
user.is_staff = False
user.is_superuser = False
user.save()

# Password value is never printed.
print(f'e2e fixture ready: username={user.username} created={created} '
      f'is_staff={user.is_staff} db={db_name}')
