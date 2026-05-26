from django.urls import path
from . import views

app_name = 'intelligence'

urlpatterns = [
    path('',                          views.hub,          name='hub'),
    path('country/<str:code>/',       views.country_detail,name='country'),
    path('compare/',                  views.compare,      name='compare'),
    path('alerts/',                   views.alerts,       name='alerts'),
    path('tracker/<str:module>/',     views.tracker,      name='tracker'),
    path('briefing/<slug:slug>/',     views.briefing,     name='briefing'),
    path('api/alerts/',               views.api_alerts,   name='api_alerts'),
    path('api/alerts/<int:alert_id>/read/', views.api_mark_read, name='api_mark_read'),
]
