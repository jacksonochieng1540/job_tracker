from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"companies", views.CompanyViewSet, basename="company")
router.register(r"resumes", views.ResumeViewSet, basename="resume")
router.register(r"job-descriptions", views.JobDescriptionViewSet, basename="jobdescription")
router.register(r"applications", views.ApplicationViewSet, basename="application")

urlpatterns = [
    # Server-rendered dashboard
    path("", views.dashboard, name="dashboard"),
    path("applications/new/", views.application_create, name="application-create"),
    path("applications/<int:pk>/", views.application_detail, name="application-detail"),
    path("resumes/", views.resume_list, name="resume-list"),

    # JSON API
    path("api/match/", views.match_preview, name="api-match-preview"),
    path("api/", include(router.urls)),
]
