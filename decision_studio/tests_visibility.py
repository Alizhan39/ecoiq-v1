"""
Who can read a question somebody else asked.

A DecisionQuery stores `session_key` and `user` because it belongs to the
visitor who asked it, and the studio list has always honoured that:
`filter(session_key=...)`, never the whole table.

The detail view did not. `get_object_or_404(DecisionQuery, pk=query_id)` on
sequential integer ids let any signed-in account walk
/decision-studio/result/1/, /2/, /3/ and read every question every other user
had ever asked — the organisations they named, what they were investigating,
which risk they were chasing before a decision.

The list filtered. The row it linked to did not. These tests hold both to the
same rule.

SCOPE OF THE EXPOSURE
---------------------
/decision-studio/ is behind core.access.ExperimentalSurfaceMiddleware, so this
was never reachable anonymously — it needed an account. That bounds the defect;
it does not excuse it. "Signed in" is not "authorised", and every account on
the platform could read every other account's questions.
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse

from decision_studio.models import DecisionQuery

ASK = '/decision-studio/ask/'
STUDIO = '/decision-studio/'


def result_url(query):
    return reverse('decision_studio:result_detail', args=[query.pk])


def signed_in_client(test, username, **flags):
    """A client signed in as its own account — one visitor, one session."""
    get_user_model().objects.create_user(username=username, password='x', **flags)
    client = test.client_class()
    client.login(username=username, password='x')
    return client


@override_settings(ALLOWED_HOSTS=['*'])
class QuestionTestCase(TestCase):
    def setUp(self):
        # The rate limiter is cache-backed and per session key; a leaked count
        # from another test would render rate_limited.html instead of asking.
        cache.clear()
        self.asker = signed_in_client(self, 'asker')

    def ask(self, client, question):
        response = client.post(ASK, {'question': question})
        self.assertEqual(response.status_code, 302,
                         f'ask did not accept the question: {response.status_code}')
        return DecisionQuery.objects.latest('pk'), response['Location']


class OwnQuestionTests(QuestionTestCase):
    """The person who asked keeps reading their own question."""

    def test_the_asker_can_read_the_result_they_were_redirected_to(self):
        """The happy path. If this breaks, the fix broke the feature."""
        query, location = self.ask(self.asker, 'Compare available companies.')
        self.assertEqual(location, result_url(query))
        self.assertEqual(self.asker.get(location).status_code, 200)

    def test_the_asker_can_come_back_to_it_later(self):
        query, _ = self.ask(self.asker, 'Compare available companies.')
        self.asker.get(STUDIO)
        self.assertEqual(self.asker.get(result_url(query)).status_code, 200)

    def test_their_own_question_is_listed_in_the_studio(self):
        self.ask(self.asker, 'Where is the evidence too weak?')
        self.assertContains(self.asker.get(STUDIO),
                            'Where is the evidence too weak?')


class SomebodyElsesQuestionTests(QuestionTestCase):
    """The defect: another account could read it by id."""

    def setUp(self):
        super().setUp()
        self.query, _ = self.ask(
            self.asker, 'Which supplier carries the transition risk?')
        self.stranger = signed_in_client(self, 'stranger')

    def test_another_account_cannot_read_it_by_id(self):
        self.assertEqual(
            self.stranger.get(result_url(self.query)).status_code, 404,
            'A second account read a question the first one asked. Sequential '
            'ids make that a walk from /result/1/ upwards.')

    def test_another_account_does_not_see_it_in_their_studio_list(self):
        self.assertNotContains(self.stranger.get(STUDIO),
                               'Which supplier carries the transition risk?')

    def test_absence_and_denial_are_indistinguishable(self):
        """
        404, not 403: whether an id has ever been asked is itself not public,
        and 403 would confirm it. Same reasoning as companies/visibility.py.
        """
        denied = self.stranger.get(result_url(self.query)).status_code
        never_existed = self.stranger.get(
            reverse('decision_studio:result_detail', args=[self.query.pk + 10_000])
        ).status_code
        self.assertEqual(denied, never_existed)

    def test_the_question_text_is_nowhere_in_the_stranger_response(self):
        """
        Belt and braces: a 404 that still rendered the question in a debug
        banner would pass the status assertion and leak anyway.
        """
        response = self.stranger.get(result_url(self.query))
        self.assertNotIn(b'transition risk', response.content)


class StaffTests(QuestionTestCase):
    """
    Staff read everything, because they already can through Django admin —
    which is where this rule would otherwise be quietly contradicted.
    """

    def setUp(self):
        super().setUp()
        self.query, _ = self.ask(self.asker, 'Rank them.')

    def test_staff_may_read_any_question(self):
        staff = signed_in_client(self, 'staffer', is_staff=True)
        self.assertEqual(staff.get(result_url(self.query)).status_code, 200)

    def test_an_ordinary_account_is_not_staff(self):
        """Guards against is_staff defaulting True and voiding every test above."""
        self.assertFalse(
            get_user_model().objects.get(username='asker').is_staff)


class FollowUpTests(QuestionTestCase):
    """
    A follow-up may only continue a question this requester asked. Unscoped,
    any id could be named as the parent, threading one account's question onto
    another's.
    """

    def setUp(self):
        super().setUp()
        self.original, _ = self.ask(self.asker, 'First question.')

    def test_a_follow_up_to_your_own_question_is_linked(self):
        follow_up, _ = self.ask(self.asker, 'And after that?')
        self.asker.post(ASK, {'question': 'And after that, again?',
                              'parent_query_id': self.original.pk})
        self.assertEqual(DecisionQuery.objects.latest('pk').parent_query_id,
                         self.original.pk)

    def test_another_account_cannot_attach_to_a_question_it_cannot_read(self):
        stranger = signed_in_client(self, 'stranger')
        stranger.post(ASK, {'question': 'Mine now.',
                            'parent_query_id': self.original.pk})
        follow_up = DecisionQuery.objects.latest('pk')
        self.assertEqual(follow_up.question_text, 'Mine now.')
        self.assertIsNone(
            follow_up.parent_query_id,
            'An account threaded its question onto one it cannot read.')

    def test_an_unreadable_parent_does_not_break_asking(self):
        """Dropping the parent must not turn into an error page."""
        stranger = signed_in_client(self, 'stranger')
        response = stranger.post(ASK, {'question': 'Still a valid question.',
                                       'parent_query_id': self.original.pk})
        self.assertEqual(response.status_code, 302)
