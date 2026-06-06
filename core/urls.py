from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    # Landing page — public homepage
    path('',                                        views.landing,           name='home'),

    # /rankings/ → canonical company rankings (alias for /companies/)
    path('rankings/', RedirectView.as_view(url='/companies/', permanent=False), name='rankings'),

    # ESG Assessment app
    path('esg/',                                    views.index,             name='index'),
    path('esg/upload/',                             views.upload,            name='upload'),
    path('esg/assessment/<int:pk>/',                views.assessment_detail, name='assessment_detail'),
    path('esg/assessment/<int:pk>/questionnaire/',  views.questionnaire,     name='questionnaire'),
    path('esg/assessment/<int:pk>/run-analysis/',   views.run_analysis,      name='run_analysis'),
    path('esg/assessment/<int:pk>/report/',         views.report,            name='report'),
    path('esg/assessment/<int:pk>/report/pdf/',     views.report_pdf,        name='report_pdf'),

    # Public share link — no auth required
    path('share/<uuid:token>/',                      views.share_report,      name='share_report'),

    # EcoIQ Methodology — public Ethical Intelligence Framework page
    path('methodology/',                             views.methodology,        name='methodology'),

    # EcoIQ About — founder story, mission, framework
    path('about/',                                   views.about,              name='about'),

    # EcoIQ Pricing — plan comparison, billing toggle, FAQ
    path('pricing/',                                 views.pricing,            name='pricing'),

    # EcoIQ API Documentation — v1 endpoints, auth, rate limits, SDK quick-start
    path('api-docs/',                                views.api_docs,           name='api_docs'),

    # EcoIQ Register — new account creation
    path('register/',                                views.register,           name='register'),

    # EcoIQ Dashboard — authenticated user home
    path('dashboard/',                               views.dashboard,          name='dashboard'),

    # /claim/ → canonical claim-profile shortcut (leads app handles the form)
    path('claim/', RedirectView.as_view(url='/request-access/claim/', permanent=False), name='claim'),

    # EcoIQ Platform — five intelligence modules overview
    path('platform/',              views.platform,              name='platform'),

    # EcoIQ Ethical Governance Intelligence Framework
    path('ethical-governance/',    views.ethical_governance,    name='ethical_governance'),

    # EcoIQ Capital Ethics Compendium — 114 governance principles
    path('governance-principles/', views.governance_principles,  name='governance_principles'),

    # EcoIQ Investors — pre-seed opportunity page
    path('investors/',          views.investors,          name='investors'),

    # EcoIQ Press — press kit, key facts, boilerplate, media contact
    path('press/',              views.press,              name='press'),

    # EcoIQ Newsletter — popup signup endpoint (JSON/AJAX, POST only)
    path('newsletter/signup/',  views.newsletter_signup,  name='newsletter_signup'),

    # EcoIQ Value Distribution — stakeholder value map + Rizq model
    path('value-distribution/', views.value_distribution, name='value_distribution'),

    # EcoIQ Sample Investor Readiness Report — public demo report
    path('sample-report/', views.sample_report, name='sample_report'),

    # EcoIQ Contact — enquiry form + founder/company details
    path('contact/',        views.contact,        name='contact'),
    path('contact/submit/', views.contact_submit, name='contact_submit'),

    # SEO — robots.txt served as plain text from templates/robots.txt
    path('robots.txt', views.robots_txt, name='robots_txt'),
]
