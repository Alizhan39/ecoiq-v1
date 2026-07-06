"""
financial_intelligence_cloud/services/accounts.py — provisioning for
institutional accounts, portfolios and portfolio entities. Idempotent via
get_or_create + explicit field sync, matching every seed command in this
repo — never delete-then-recreate.
"""
from financial_intelligence_cloud.models import InstitutionalAccount, Portfolio, PortfolioEntity


def create_institutional_account(slug, firm_name, account_type, subscription_tier='starter', **fields):
    account, _ = InstitutionalAccount.objects.get_or_create(slug=slug, defaults={'firm_name': firm_name, 'account_type': account_type})
    account.firm_name = firm_name
    account.account_type = account_type
    account.subscription_tier = subscription_tier
    account.subscription_price_label = fields.pop(
        'subscription_price_label',
        'Contact / Custom' if subscription_tier == 'institutional' else account.subscription_price_label or 'Contact / Custom',
    )
    for field, value in fields.items():
        setattr(account, field, value)
    account.save()
    return account


def create_portfolio(institutional_account, name, portfolio_type, **fields):
    portfolio, _ = Portfolio.objects.get_or_create(
        institutional_account=institutional_account, name=name, defaults={'portfolio_type': portfolio_type},
    )
    portfolio.portfolio_type = portfolio_type
    for field, value in fields.items():
        setattr(portfolio, field, value)
    portfolio.save()
    return portfolio


def add_portfolio_entity(portfolio, name, entity_type, **fields):
    """Creates/updates one PortfolioEntity and keeps Portfolio.entity_count in sync."""
    entity, _ = PortfolioEntity.objects.get_or_create(
        portfolio=portfolio, name=name, defaults={'entity_type': entity_type},
    )
    entity.entity_type = entity_type
    for field, value in fields.items():
        setattr(entity, field, value)
    entity.save()

    portfolio.entity_count = portfolio.entities.count()
    portfolio.save(update_fields=['entity_count'])
    return entity
