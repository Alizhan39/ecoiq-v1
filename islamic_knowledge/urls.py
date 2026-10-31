from django.urls import path
from . import views

app_name = 'islamic_knowledge'
urlpatterns = [
    path('sources/', views.sources, name='sources'),
    path('surahs/', views.surah_index, name='surahs'),
    path('names/', views.name_index, name='names'),
    path('passages/', views.passages, name='passages'),
    path('search/', views.search, name='search'),
]
