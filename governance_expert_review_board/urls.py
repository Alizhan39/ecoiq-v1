"""governance_expert_review_board/urls.py — routes (mounted at /governance-expert-review-board/)."""
from django.urls import path

from governance_expert_review_board import views

app_name = 'governance_expert_review_board'

urlpatterns = [
    path('', views.overview, name='overview'),
]
