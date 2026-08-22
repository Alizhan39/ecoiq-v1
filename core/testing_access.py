"""
core/testing_access.py — a signed-in test client for the de-published surfaces.

The pages under core.access.SIGN_IN_PREFIXES stopped answering anonymously, so
the suites that exercise them have to sign in. Their subject did not change:
they still assert what the view renders, and they should keep asserting it.

`_pre_setup` rather than `setUp`, deliberately. It runs after the test database
is ready and before the test's own setUp, so a suite with an existing setUp
inherits the signed-in client without that setUp being touched or having to
remember to call super() in the right order.

This is a test helper for an ACCESS change, not a way to skip the gate: the
gate's own behaviour — who is turned away, and where the public surface is left
alone — is asserted in core/tests_access.py against an anonymous client.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model


class SignedIn:
    """Mixin: give `self.client` a signed-in ordinary (non-staff) user."""

    #: Ordinary user on purpose. A staff user would also pass the
    #: @staff_member_required decorators these apps already carry, which would
    #: quietly stop testing them.
    signed_in_username = 'internal-surface-tester'

    def _pre_setup(self):
        super()._pre_setup()
        # No password. `force_login` skips authentication entirely, so setting
        # one would be a literal credential in a tracked file for no benefit —
        # which core/tests_no_hardcoded_secrets.py correctly refuses, and did.
        user = get_user_model().objects.create_user(
            username=self.signed_in_username)
        self.client.force_login(user)
        self.signed_in_user = user
