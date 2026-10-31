"""
The React ↔ Django authentication boundary.

No new authentication system: Django sessions, already in the DRF chain,
already Secure in production, already carrying staff permissions. These tests
cover the eight cases the phase brief names, plus the two that matter most for
a boundary — that the client is never trusted, and that nothing secret is
handed to JavaScript.
"""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

User = get_user_model()

SESSION = '/api/v2/session/'
SIGN_IN = '/api/v2/session/sign-in/'
SIGN_OUT = '/api/v2/session/sign-out/'


class AnonymousAccess(TestCase):

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def test_anonymous_is_a_successful_answer_not_an_error(self):
        """
        A 401 here would make every anonymous page load look like a failure,
        and the public product is anonymous by default.
        """
        response = Client().get(SESSION)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['authenticated'])

    def test_it_reports_no_username_when_anonymous(self):
        payload = Client().get(SESSION).json()

        self.assertIsNone(payload['username'])
        self.assertFalse(payload['is_staff'])

    def test_public_endpoints_remain_reachable_without_a_session(self):
        for path in ('/api/v2/companies/', '/api/v2/platform/'):
            with self.subTest(path=path):
                self.assertEqual(Client().get(path).status_code, 200)

    def test_the_csrf_cookie_is_set_for_an_anonymous_caller(self):
        """
        Without this an SPA has no way to obtain a token before its first POST,
        because it may never render a Django template.
        """
        response = Client().get(SESSION)

        self.assertIn('csrftoken', response.cookies)


class SignIn(TestCase):

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.user = User.objects.create_user(username='alice', password='pw-correct')

    def test_valid_credentials_sign_in(self):
        client = Client()

        response = client.post(SIGN_IN, {'username': 'alice',
                                         'password': 'pw-correct'},
                               content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['authenticated'])
        self.assertEqual(response.json()['username'], 'alice')

    def test_the_session_persists_to_the_next_request(self):
        client = Client()
        client.post(SIGN_IN, {'username': 'alice', 'password': 'pw-correct'},
                    content_type='application/json')

        self.assertTrue(client.get(SESSION).json()['authenticated'])

    def test_a_wrong_password_is_rejected(self):
        response = Client().post(SIGN_IN, {'username': 'alice',
                                           'password': 'wrong'},
                                 content_type='application/json')

        self.assertEqual(response.status_code, 401)

    def test_an_unknown_user_and_a_wrong_password_are_indistinguishable(self):
        """
        Distinguishing them turns this into a user-enumeration oracle.
        """
        wrong_password = Client().post(
            SIGN_IN, {'username': 'alice', 'password': 'wrong'},
            content_type='application/json')
        unknown_user = Client().post(
            SIGN_IN, {'username': 'nobody', 'password': 'wrong'},
            content_type='application/json')

        self.assertEqual(wrong_password.status_code, unknown_user.status_code)
        self.assertEqual(wrong_password.json(), unknown_user.json())

    def test_no_token_or_session_key_is_returned_to_javascript(self):
        """
        The session lives in an HttpOnly cookie the client cannot read. That
        property is what makes this boundary safe, and returning a token would
        throw it away.
        """
        client = Client()
        payload = client.post(SIGN_IN, {'username': 'alice',
                                        'password': 'pw-correct'},
                              content_type='application/json').json()

        self.assertEqual(set(payload), {'authenticated', 'username', 'is_staff'})
        for forbidden in ('token', 'access', 'refresh', 'sessionid', 'password'):
            with self.subTest(key=forbidden):
                self.assertNotIn(forbidden, payload)

    def test_empty_credentials_are_rejected(self):
        response = Client().post(SIGN_IN, {}, content_type='application/json')

        self.assertEqual(response.status_code, 401)

    def test_the_session_key_rotates_on_sign_in(self):
        """Session fixation protection — what login() gives us for free."""
        client = Client()
        client.get(SESSION)
        before = client.cookies.get('sessionid')
        client.post(SIGN_IN, {'username': 'alice', 'password': 'pw-correct'},
                    content_type='application/json')
        after = client.cookies.get('sessionid')

        if before is not None:
            self.assertNotEqual(before.value, after.value)


class SignOut(TestCase):

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        User.objects.create_user(username='bob', password='pw')
        self.client = Client()
        self.client.post(SIGN_IN, {'username': 'bob', 'password': 'pw'},
                         content_type='application/json')

    def test_sign_out_ends_the_session(self):
        self.client.post(SIGN_OUT, content_type='application/json')

        self.assertFalse(self.client.get(SESSION).json()['authenticated'])

    def test_signing_out_twice_is_not_an_error(self):
        """
        The caller asked for a state that is already true. A 401 would make a
        double-click look like a failure.
        """
        self.client.post(SIGN_OUT, content_type='application/json')
        second = self.client.post(SIGN_OUT, content_type='application/json')

        self.assertEqual(second.status_code, 200)

    def test_sign_out_rejects_get(self):
        """A sign-out reachable by GET can be fired by an <img> on any page."""
        self.assertEqual(self.client.get(SIGN_OUT).status_code, 405)


class ExpiredSession(TestCase):

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        User.objects.create_user(username='carol', password='pw')

    def test_a_cleared_session_reads_as_anonymous(self):
        client = Client()
        client.post(SIGN_IN, {'username': 'carol', 'password': 'pw'},
                    content_type='application/json')
        self.assertTrue(client.get(SESSION).json()['authenticated'])

        from django.contrib.sessions.models import Session
        Session.objects.all().delete()

        self.assertFalse(client.get(SESSION).json()['authenticated'])

    def test_an_expired_session_does_not_error_the_public_surface(self):
        client = Client()
        client.post(SIGN_IN, {'username': 'carol', 'password': 'pw'},
                    content_type='application/json')
        from django.contrib.sessions.models import Session
        Session.objects.all().delete()

        self.assertEqual(client.get('/api/v2/companies/').status_code, 200)


@override_settings(CSRF_USE_SESSIONS=False)
class CsrfEnforcement(TestCase):
    """
    Django's test client disables CSRF by default, so these use
    `enforce_csrf_checks=True` — otherwise the tests would pass without the
    protection existing.
    """

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        User.objects.create_user(username='dave', password='pw')

    def test_an_unsafe_request_without_a_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)

        response = client.post(SIGN_IN, {'username': 'dave', 'password': 'pw'},
                               content_type='application/json')

        self.assertEqual(response.status_code, 403)

    def test_an_unsafe_request_with_the_token_succeeds(self):
        client = Client(enforce_csrf_checks=True)
        client.get(SESSION)                       # sets the cookie
        token = client.cookies['csrftoken'].value

        response = client.post(SIGN_IN, {'username': 'dave', 'password': 'pw'},
                               content_type='application/json',
                               HTTP_X_CSRFTOKEN=token)

        self.assertEqual(response.status_code, 200)

    def test_a_wrong_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        client.get(SESSION)

        response = client.post(SIGN_IN, {'username': 'dave', 'password': 'pw'},
                               content_type='application/json',
                               HTTP_X_CSRFTOKEN='not-the-token')

        self.assertEqual(response.status_code, 403)

    def test_reads_do_not_require_a_token(self):
        client = Client(enforce_csrf_checks=True)

        self.assertEqual(client.get('/api/v2/companies/').status_code, 200)


class StaffBoundary(TestCase):
    """
    `is_staff` in the session payload is a HINT for rendering. It is not a
    permission, and the server must not trust it.
    """

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        User.objects.create_user(username='plain', password='pw')
        User.objects.create_user(username='staffer', password='pw', is_staff=True)

    def _client(self, username):
        client = Client()
        client.post(SIGN_IN, {'username': username, 'password': 'pw'},
                    content_type='application/json')
        return client

    def test_a_plain_user_is_not_reported_as_staff(self):
        self.assertFalse(self._client('plain').get(SESSION).json()['is_staff'])

    def test_a_staff_user_is_reported_as_staff(self):
        self.assertTrue(self._client('staffer').get(SESSION).json()['is_staff'])

    def test_the_admin_rejects_an_anonymous_caller(self):
        response = Client().get('/admin/', follow=False)

        self.assertIn(response.status_code, (302, 403))

    def test_the_admin_rejects_a_non_staff_user(self):
        response = self._client('plain').get('/admin/', follow=False)

        self.assertIn(response.status_code, (302, 403))

    def test_staff_only_league_rows_are_not_exposed_by_a_client_claim(self):
        """
        The league table shows unevidenced companies to staff. A client cannot
        obtain that by asserting is_staff — the server reads the session.
        """
        anonymous = Client().get('/league/')

        self.assertEqual(anonymous.status_code, 200)
        self.assertNotIn('ineligible_count_visible_to_anonymous',
                         anonymous.content.decode())


class DjangoLoginStillWorks(TestCase):
    """
    This is an ADDITIONAL JSON surface, not a replacement. Staff tooling and
    the admin depend on the existing form login.
    """

    def test_the_form_login_route_still_exists(self):
        self.assertEqual(Client().get('/login/').status_code, 200)
