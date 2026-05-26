from django.urls import path
from . import views

app_name = 'transition'

urlpatterns = [
    path('',                                  views.index,              name='index'),
    path('financing/',                        views.financing_directory, name='financing'),
    path('financing/<int:pk>/',              views.financing_detail,    name='financing_detail'),
    path('<slug:slug>/',                      views.dashboard,           name='dashboard'),
    path('<slug:slug>/generate/',             views.generate_roadmap,    name='generate'),
    path('<slug:slug>/roadmap/<int:pk>/',    views.roadmap_detail,      name='roadmap'),
    path('api/roadmap/<int:pk>/status/',     views.api_roadmap_status,  name='api_roadmap_status'),
]
