"""
ml/clustering.py — K-Means clustering for EcoIQ company peer groups.

Clusters companies into 6 archetypes with human-readable labels.
Label assignment uses centroid averages of key pillar scores.

Usage:
    from ml.clustering import CompanyClusterer
    clusterer = CompanyClusterer()
    clusterer.train(apply=True)
"""
from __future__ import annotations

import logging
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)

MODEL_PATH  = Path(__file__).resolve().parent / 'models' / 'cluster_kmeans.joblib'
SCALER_PATH = Path(__file__).resolve().parent / 'models' / 'cluster_scaler.joblib'

# Number of clusters
N_CLUSTERS = 6

# Archetype labels: assigned post-hoc based on centroid characteristics
# (pollution low + transparency high → ESG Leader, etc.)
# Actual assignment done dynamically in _label_clusters()
ARCHETYPE_TEMPLATES = [
    'ESG Leader',
    'Climate Transformer',
    'Ethical Employer',
    'Governance Champion',
    'Emerging Improver',
    'High-Risk Laggard',
]


class CompanyClusterer:
    """K-Means peer-group clusterer."""

    def __init__(self, n_clusters: int = N_CLUSTERS):
        self.n_clusters = n_clusters
        self.model      = None
        self.scaler     = None
        self._labels: dict[int, str] = {}
        self._loaded = False

    def _load(self) -> bool:
        if self._loaded:
            return True
        try:
            import joblib
            self.model  = joblib.load(MODEL_PATH)
            self.scaler = joblib.load(SCALER_PATH)
            # Try to load label map
            label_path = MODEL_PATH.parent / 'cluster_labels.joblib'
            if label_path.exists():
                self._labels = joblib.load(label_path)
            self._loaded = True
            return True
        except Exception as exc:
            logger.warning('Clustering model not loaded: %s', exc)
            return False

    def train(self, companies=None, apply: bool = False) -> dict:
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
        import joblib
        from league.models import Company
        from ml.features import company_to_vector, get_feature_names

        if companies is None:
            companies = list(
                Company.objects.filter(ecoiq_score__gt=0).select_related('profile')
            )

        X_rows, ids = [], []
        for company in companies:
            try:
                vec = company_to_vector(company)
                X_rows.append(vec)
                ids.append(company.pk)
            except Exception as exc:
                logger.debug('Feature extraction failed for %s: %s', company, exc)

        if len(X_rows) < self.n_clusters:
            return {'error': 'insufficient_data', 'n_samples': len(X_rows)}

        X = np.array(X_rows, dtype=np.float64)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Use k-means++ initialisation for better centroids
        n_c = min(self.n_clusters, len(X_rows))
        km = KMeans(
            n_clusters=n_c,
            init='k-means++',
            n_init=20,
            random_state=42,
        )
        km.fit(X_scaled)

        # Assign human labels to cluster indices based on centroid profiles
        feature_names = get_feature_names()
        labels = self._label_clusters(km.cluster_centers_, feature_names, n_c)
        self._labels = labels

        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(km,     MODEL_PATH)
        joblib.dump(scaler, SCALER_PATH)
        joblib.dump(labels, MODEL_PATH.parent / 'cluster_labels.joblib')
        self.model   = km
        self.scaler  = scaler
        self._loaded = True

        cluster_counts = dict(zip(*np.unique(km.labels_, return_counts=True)))
        logger.info('K-Means trained: n=%d, clusters=%s', len(X_rows), cluster_counts)

        if apply:
            cluster_assignments = km.predict(X_scaled)
            self._apply(ids, cluster_assignments)

        return {
            'n_samples':      len(X_rows),
            'n_clusters':     n_c,
            'cluster_labels': labels,
            'cluster_sizes':  {int(k): int(v) for k, v in cluster_counts.items()},
        }

    def _label_clusters(
        self,
        centers: np.ndarray,
        feature_names: list[str],
        n_clusters: int,
    ) -> dict[int, str]:
        """
        Assign archetype names by sorting centroids along key axes.

        Scoring proxy: use a weighted sum of key features to rank clusters
        from 'highest performing' to 'lowest', then assign archetype names
        in that order.
        """
        # Feature indices for key signals
        fi = {name: i for i, name in enumerate(feature_names)}

        def cluster_score(center):
            env   = center[fi.get('environmental_responsibility_score', 0)]
            trans = center[fi.get('transparency_anti_corruption_score', 1)]
            pb    = center[fi.get('public_benefit_score', 2)]
            harm  = center[fi.get('harm_penalty', 11)]
            poll  = center[fi.get('pollution_level_enc', 20)]
            return env + trans + pb - harm * 10 - poll * 5

        scores = [(i, cluster_score(centers[i])) for i in range(n_clusters)]
        scores.sort(key=lambda t: t[1], reverse=True)

        templates = list(ARCHETYPE_TEMPLATES[:n_clusters])
        # Pad if n_clusters > templates
        while len(templates) < n_clusters:
            templates.append(f'Peer Group {len(templates) + 1}')

        return {cluster_idx: templates[rank] for rank, (cluster_idx, _) in enumerate(scores)}

    def _apply(self, ids, cluster_assignments):
        """Write ml_cluster and ml_cluster_label to Company records."""
        from django.utils import timezone
        from league.models import Company

        for pk, cluster_idx in zip(ids, cluster_assignments):
            label = self._labels.get(int(cluster_idx), f'Cluster {cluster_idx}')
            Company.objects.filter(pk=pk).update(
                ml_cluster=int(cluster_idx),
                ml_cluster_label=label,
                ml_last_run=timezone.now(),
            )

    def assign_company(self, company) -> dict | None:
        """Assign a single company to a cluster."""
        if not self._load():
            return None
        from ml.features import company_to_vector
        try:
            vec   = company_to_vector(company).reshape(1, -1)
            scaled = self.scaler.transform(vec)
            cluster_idx = int(self.model.predict(scaled)[0])
            label = self._labels.get(cluster_idx, f'Cluster {cluster_idx}')
            return {'cluster': cluster_idx, 'label': label}
        except Exception as exc:
            logger.error('Cluster assignment failed for %s: %s', company, exc)
            return None
