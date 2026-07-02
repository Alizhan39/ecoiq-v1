"""executive_briefing_board_pack_generator/urls.py — routes (mounted at /executive-briefing-board-pack-generator/)."""
from django.urls import path

from executive_briefing_board_pack_generator import views

app_name = 'executive_briefing_board_pack_generator'

urlpatterns = [
    path('', views.overview, name='overview'),
]
