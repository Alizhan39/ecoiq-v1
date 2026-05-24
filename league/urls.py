from django.urls import path
from . import views

app_name = 'league'

urlpatterns = [
    path('',         views.leaderboard,    name='leaderboard'),
    path('<slug:slug>/', views.company_profile, name='company'),
]
