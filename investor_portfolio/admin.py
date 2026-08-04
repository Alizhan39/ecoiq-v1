from django.contrib import admin

from .models import (
    Holding, Portfolio, PortfolioBriefing, PortfolioSnapshot, Watchlist, WatchlistItem,
)


class WatchlistItemInline(admin.TabularInline):
    model = WatchlistItem
    extra = 0


@admin.register(Watchlist)
class WatchlistAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'is_public', 'item_count', 'updated_at']
    list_filter = ['is_public']
    search_fields = ['name', 'owner__username']
    inlines = [WatchlistItemInline]

    @admin.display(description='Companies')
    def item_count(self, obj):
        return obj.items.count()


class HoldingInline(admin.TabularInline):
    model = Holding
    extra = 0


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'base_currency', 'holding_count', 'updated_at']
    search_fields = ['name', 'owner__username']
    inlines = [HoldingInline]

    @admin.display(description='Holdings')
    def holding_count(self, obj):
        return obj.holdings.count()


@admin.register(PortfolioSnapshot)
class PortfolioSnapshotAdmin(admin.ModelAdmin):
    list_display = ['portfolio', 'calculated_at', 'exposure_score', 'unknown_exposure_pct',
                     'total_market_value', 'fx_incomplete']
    list_filter = ['fx_incomplete', 'methodology_version']
    readonly_fields = [f.name for f in PortfolioSnapshot._meta.fields]

    def has_add_permission(self, request):
        return False  # snapshots are only ever created by calculations.py


@admin.register(PortfolioBriefing)
class PortfolioBriefingAdmin(admin.ModelAdmin):
    list_display = ['portfolio', 'version', 'status', 'generated_at', 'reviewed_by', 'published_at']
    list_filter = ['status', 'model_provider']
    readonly_fields = [
        'portfolio', 'snapshot', 'version', 'content', 'model_name', 'model_provider',
        'routing_reason', 'prompt_version', 'methodology_version', 'prohibited_language_flags',
        'generated_at', 'generated_by',
    ]
