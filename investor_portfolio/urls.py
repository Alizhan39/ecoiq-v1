from django.urls import path

from . import views

app_name = 'portfolio'

urlpatterns = [
    # Watchlists
    path('watchlists/', views.watchlist_list, name='watchlist_list'),
    path('watchlists/new/', views.watchlist_create, name='watchlist_create'),
    path('watchlists/add/', views.watchlist_add_company, name='watchlist_add_company'),
    path('watchlists/<int:pk>/', views.watchlist_detail, name='watchlist_detail'),
    path('watchlists/<int:pk>/delete/', views.watchlist_delete, name='watchlist_delete'),
    path('watchlists/<int:pk>/remove/<slug:company_slug>/', views.watchlist_remove_company,
         name='watchlist_remove_company'),

    # Portfolios
    path('', views.portfolio_list, name='portfolio_list'),
    path('new/', views.portfolio_create, name='portfolio_create'),
    path('<int:pk>/', views.portfolio_dashboard, name='portfolio_dashboard'),
    path('<int:pk>/delete/', views.portfolio_delete, name='portfolio_delete'),
    path('<int:pk>/recalculate/', views.portfolio_recalculate, name='portfolio_recalculate'),

    # Holdings
    path('<int:pk>/holdings/add/', views.holding_create, name='holding_create'),
    path('<int:pk>/holdings/<int:holding_id>/edit/', views.holding_edit, name='holding_edit'),
    path('<int:pk>/holdings/<int:holding_id>/delete/', views.holding_delete, name='holding_delete'),

    # CSV import / export
    path('<int:pk>/import/', views.portfolio_import_csv, name='portfolio_import_csv'),
    path('<int:pk>/import/confirm/', views.portfolio_import_confirm, name='portfolio_import_confirm'),
    path('<int:pk>/export/', views.portfolio_export_csv, name='portfolio_export_csv'),

    # AI briefing
    path('<int:pk>/briefing/generate/', views.portfolio_generate_briefing, name='portfolio_generate_briefing'),
    path('<int:pk>/briefing/<int:briefing_id>/status/', views.portfolio_briefing_status,
         name='portfolio_briefing_status'),
]
