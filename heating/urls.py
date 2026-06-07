from django.urls import path
from . import views

app_name = 'heating'

urlpatterns = [
    path('',                     views.overview,            name='overview'),
    path('packages/',            views.packages,            name='packages'),
    path('calculator/',          views.calculator,          name='calculator'),
    path('company-sponsorship/', views.company_sponsorship, name='company_sponsorship'),
    path('pilot-application/',   views.pilot_application,    name='pilot_application'),
]
