"""
financial_intelligence_cloud/services/subscription.py — thin subscription-
tier feature-gate stub. No billing/Stripe integration; this dict is the
single source of truth for which features each tier unlocks, mirroring the
shape of agent_runtime_model_router's AGENT_METADATA_BY_FOLDER pattern.
"""
SUBSCRIPTION_TIER_FEATURES = {
    'starter': {
        'client_opportunity_radar', 'daily_brief',
    },
    'professional': {
        'client_opportunity_radar', 'daily_brief', 'opportunity_feed', 'ask', 'white_label',
    },
    'institutional': {
        'client_opportunity_radar', 'daily_brief', 'opportunity_feed', 'ask', 'white_label', 'capital_allocation',
    },
}


def has_feature(institutional_account, feature_name):
    return feature_name in SUBSCRIPTION_TIER_FEATURES.get(institutional_account.subscription_tier, set())
