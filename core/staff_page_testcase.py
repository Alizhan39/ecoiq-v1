"""
Shared base for tests of pages that are staff-only.

Deliberately NOT named `test*.py`: this module defines no tests of its own, and
the default runner pattern would otherwise try to collect it.

Why this exists
---------------
The internal concept pages gated in PR A (see
docs/product/PHASE_1_ARCHITECTURE.md §3) each had a `<App>PageTests` class whose
assertions were written against anonymous access. Gating the views made every one
of those assertions fail with `302 != 200`.

The right fix is not to weaken those assertions — they check real things, like
that a page renders its heading and contains no unrendered template tokens. It is
to run them as the audience that is now allowed to see the page. Inheriting from
this class keeps every existing assertion intact and changes only who is asking.

A test that wants to assert the *anonymous* behaviour should use a plain
`TestCase` and a fresh `Client`; see `core/tests_internal_page_gating.py`, which
owns that side of the contract.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase


class StaffPageTestCase(TestCase):
    """A TestCase whose `self.client` is already signed in as a staff user."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # No password argument: force_login() below never checks one, so setting
        # a literal here would add an unused credential to a module that
        # core/tests_no_hardcoded_secrets.py scans as runtime code. This file is
        # deliberately not named tests_*, so it is not covered by that guard's
        # TEST_FILE_MARKERS exclusion — and it should not need to be.
        cls.staff_user = get_user_model().objects.create_user(
            username='staff-page-tests',
            email='staff-page-tests@example.com',
            is_staff=True,
        )

    def setUp(self):
        super().setUp()
        # force_login rather than login(): no password hashing per test, and it
        # cannot start failing because of an unrelated auth-backend change.
        self.client.force_login(self.staff_user)
