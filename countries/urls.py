from django.urls import path
from countries import views

app_name = 'countries'

urlpatterns = [
    path('',          views.country_directory, name='directory'),
    path('<slug:slug>/', views.country_detail,  name='detail'),
]
