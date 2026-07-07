"""khalifa_stewardship_tour_operating_system/urls.py — routes (mounted at /khalifa-tour-operating-system/)."""
from django.urls import path

from khalifa_stewardship_tour_operating_system import views

app_name = 'khalifa_stewardship_tour_operating_system'

urlpatterns = [
    path('', views.overview, name='overview'),
    path('presentation/', views.presentation, name='presentation'),
    path('tours/', views.tours, name='tours'),
    path('tour/<slug:slug>/', views.tour_detail, name='tour_detail'),
    path('problems/', views.problems, name='problems'),
    path('funding/', views.funding, name='funding'),
    path('mrv/', views.mrv, name='mrv'),
    path('legacy/', views.legacy, name='legacy'),
    path('kazakhstan-clean-heat-demo/', views.kazakhstan_demo, name='kazakhstan_demo'),
    path('real-pilot-readiness/', views.real_pilot_readiness, name='real_pilot_readiness'),
]
