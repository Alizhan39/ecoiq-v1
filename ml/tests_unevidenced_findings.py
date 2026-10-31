"""
What the ML surfaces say about an organisation nobody has measured.

`ml.features.company_to_vector` imputes 50.0 for every input it does not know
— deliberately, to match the fitted artefact — and its docstring says so:

    Check missing_material_features() BEFORE calling this if the result will be
    presented as a finding about the company.

`EcoIQScoringModel.predict_company` honoured that and refuses. Its two siblings
did not, and both are published as findings by
/companies/<slug>/ml-insights.json. Measured against an organisation holding no
data at all:

    {"scoring": null,
     "prediction": null,
     "anomaly": {"anomaly_score": -0.45, "is_anomaly": false},
     "cluster":  {"cluster": 5, "label": "Governance Champion"}}

Two refused. Two answered — with a commendation and a clean bill of health,
both assembled entirely from the imputed average. `is_anomaly: false` is the
worse of the pair: it reads as "we looked and found nothing unusual" when
nothing was looked at, and it is the reassuring direction.
"""
from unittest import mock

from django.test import TestCase
from django.test.utils import override_settings

from companies.models import CompanyProfile
from league.models import Company
from ml.features import missing_material_features


def unmeasured_company(slug='unmeasured'):
    company = Company.objects.create(name='Unmeasured Co', slug=slug)
    CompanyProfile.objects.create(company=company)
    return company


class PremiseTests(TestCase):
    """If these stop holding, every assertion below is testing nothing."""

    def test_an_organisation_with_no_data_has_missing_material_features(self):
        self.assertTrue(missing_material_features(unmeasured_company()))

    def test_the_vector_imputes_rather_than_refusing(self):
        """
        The imputation is deliberate and stays. The boundary moves, not the
        feature extraction — that is what these guards are.
        """
        from ml.features import company_to_vector

        vector = company_to_vector(unmeasured_company())
        self.assertIn(50.0, list(vector))


class RefusalTests(TestCase):
    """A model that only saw defaults must not describe the organisation."""

    def setUp(self):
        self.company = unmeasured_company()

    def test_clustering_refuses(self):
        """
        The model is stubbed to WORK, so a None here can only be the guard.
        Left unstubbed, the unloaded artefact raises into the except block and
        returns None anyway — which looks identical from outside and would let
        this pass with the guard removed.
        """
        import numpy as np

        from ml.clustering import CompanyClusterer

        clusterer = CompanyClusterer()
        clusterer.model = mock.Mock()
        clusterer.model.predict.return_value = np.array([5])
        clusterer.scaler = mock.Mock()
        clusterer.scaler.transform.side_effect = lambda vec: vec
        clusterer._labels = {5: 'Governance Champion'}

        with mock.patch.object(clusterer, '_load', return_value=True):
            self.assertIsNone(
                clusterer.assign_company(self.company),
                'An organisation with no data was given a cluster label — a '
                'judgement read off the imputed average.')

    def test_anomaly_scoring_refuses(self):
        """Stubbed to work, for the same reason as above."""
        import numpy as np

        from ml.anomaly_detection import AnomalyDetector

        detector = AnomalyDetector()
        detector.model = mock.Mock()
        detector.model.score_samples.return_value = np.array([-0.45])
        detector.model.predict.return_value = np.array([1])
        detector.scaler = mock.Mock()
        detector.scaler.transform.side_effect = lambda vec: vec

        with mock.patch.object(detector, '_load', return_value=True):
            self.assertIsNone(
                detector.score_company(self.company),
                '"is_anomaly: false" for an organisation nobody looked at '
                'reads as a clean bill of health.')

    def test_it_refuses_before_touching_the_model(self):
        """
        The guard runs first, so the refusal is a decision — not an
        exception swallowed by the try block, which would return None for a
        completely different reason and look identical from outside.
        """
        from ml.clustering import CompanyClusterer

        clusterer = CompanyClusterer()
        clusterer.model = mock.Mock()
        clusterer.scaler = mock.Mock()
        with mock.patch.object(clusterer, '_load', return_value=True):
            self.assertIsNone(clusterer.assign_company(self.company))
        clusterer.model.predict.assert_not_called()
        clusterer.scaler.transform.assert_not_called()


class MeasuredOrganisationsAreStillServedTests(TestCase):
    """
    The control. Refusing for everybody would satisfy the tests above while
    removing the capability.
    """

    def setUp(self):
        from ml.tests_unknown_propagation import _profile

        self.profile = _profile('ml-known')

    def test_a_fully_measured_organisation_has_nothing_missing(self):
        self.assertEqual(missing_material_features(self.profile.company), [])

    def test_a_measured_organisation_still_reaches_the_model(self):
        """
        Proven by the model actually being consulted, not by a None that could
        mean either thing.
        """
        import numpy as np

        from ml.clustering import CompanyClusterer

        clusterer = CompanyClusterer()
        clusterer.model = mock.Mock()
        clusterer.model.predict.return_value = np.array([2])
        clusterer.scaler = mock.Mock()
        clusterer.scaler.transform.side_effect = lambda vec: vec
        clusterer._labels = {2: 'Measured Label'}

        with mock.patch.object(clusterer, '_load', return_value=True):
            result = clusterer.assign_company(self.profile.company)

        clusterer.model.predict.assert_called_once()
        self.assertEqual(result, {'cluster': 2, 'label': 'Measured Label'})


@override_settings(ALLOWED_HOSTS=['*'])
class MlInsightsPayloadTests(TestCase):
    """The surface that publishes it."""

    def test_no_judgement_label_is_returned_for_an_unmeasured_organisation(self):
        company = unmeasured_company('payload-co')
        CompanyProfile.objects.filter(company=company).update(status='public')
        payload = self.client.get(
            f'/companies/{company.slug}/ml-insights.json').json()
        self.assertIsNone(payload['cluster'],
                          f"cluster was {payload['cluster']!r}")
        self.assertIsNone(payload['anomaly'],
                          f"anomaly was {payload['anomaly']!r}")

    def test_the_endpoint_still_answers(self):
        """
        Refusing a finding is not the same as failing. The caller gets a
        well-formed payload whose fields are explicitly null.
        """
        company = unmeasured_company('payload-co-2')
        CompanyProfile.objects.filter(company=company).update(status='public')
        response = self.client.get(f'/companies/{company.slug}/ml-insights.json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()) >= {
            'company', 'slug', 'scoring', 'anomaly', 'cluster', 'prediction',
            'error'}, True)
