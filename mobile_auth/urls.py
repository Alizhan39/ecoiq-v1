"""mobile_auth/urls.py — mounted at /api/v1/auth/ from api/urls.py."""
from django.urls import path

from . import views

app_name = 'mobile_auth'

urlpatterns = [
    path('login/',                    views.LoginView.as_view(),          name='login'),
    path('refresh/',                  views.RefreshView.as_view(),        name='refresh'),
    path('logout/',                   views.LogoutView.as_view(),         name='logout'),
    path('logout-all/',               views.LogoutAllView.as_view(),      name='logout_all'),
    path('sessions/',                 views.SessionListView.as_view(),    name='sessions'),
    path('sessions/<int:session_id>/revoke/', views.SessionRevokeView.as_view(), name='session_revoke'),
]
