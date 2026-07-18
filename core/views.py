from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages

from .models import Company, Resume, JobDescription, Application
from .serializers import (
    CompanySerializer, ResumeSerializer, JobDescriptionSerializer,
    ApplicationSerializer, MatchRequestSerializer, MatchResultSerializer,
)
from .matching import compute_match


class OwnerScopedMixin:
    def get_queryset(self):
        return self.queryset.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class CompanyViewSet(OwnerScopedMixin, viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]


class ResumeViewSet(OwnerScopedMixin, viewsets.ModelViewSet):
    queryset = Resume.objects.all()
    serializer_class = ResumeSerializer
    permission_classes = [permissions.IsAuthenticated]


class JobDescriptionViewSet(OwnerScopedMixin, viewsets.ModelViewSet):
    queryset = JobDescription.objects.all()
    serializer_class = JobDescriptionSerializer
    permission_classes = [permissions.IsAuthenticated]


class ApplicationViewSet(OwnerScopedMixin, viewsets.ModelViewSet):
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=["post"])
    def recompute_match(self, request, pk=None):
        """POST /api/applications/{id}/recompute_match/ -> refreshes match_score."""
        application = self.get_object()
        resume_text = application.resume.content if application.resume else ""
        jd_text = application.job_description.content
        result = compute_match(resume_text, jd_text)
        application.match_score = result["score"]
        application.missing_keywords = result["missing_keywords"]
        application.save(update_fields=["match_score", "missing_keywords"])
        return Response(ApplicationSerializer(application).data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def match_preview(request):
    """
    POST /api/match/ {resume_text, jd_text}
    Standalone matcher — lets a user test a match before creating an Application.
    """
    req = MatchRequestSerializer(data=request.data)
    req.is_valid(raise_exception=True)
    result = compute_match(req.validated_data["resume_text"], req.validated_data["jd_text"])
    return Response(MatchResultSerializer(result).data, status=status.HTTP_200_OK)

@login_required
def dashboard(request):
    """Kanban-style board: applications grouped by status column."""
    applications = Application.objects.filter(owner=request.user).select_related("company", "job_description")
    columns = {choice_value: [] for choice_value, _ in Application.Status.choices}
    for app_obj in applications:
        columns[app_obj.status].append(app_obj)
    context = {
        "columns": columns,
        "status_labels": dict(Application.Status.choices),
        "total": applications.count(),
    }
    return render(request, "core/dashboard.html", context)


@login_required
def application_create(request):
    companies = Company.objects.filter(owner=request.user)
    resumes = Resume.objects.filter(owner=request.user)

    if request.method == "POST":
        company_id = request.POST.get("company")
        new_company_name = request.POST.get("new_company_name", "").strip()
        role_title = request.POST.get("role_title", "").strip()
        jd_title = request.POST.get("jd_title", "").strip()
        jd_content = request.POST.get("jd_content", "").strip()
        source_url = request.POST.get("source_url", "").strip()
        resume_id = request.POST.get("resume")

        if new_company_name:
            company, _ = Company.objects.get_or_create(owner=request.user, name=new_company_name)
        else:
            company = get_object_or_404(Company, pk=company_id, owner=request.user)

        job_description = JobDescription.objects.create(
            owner=request.user, title=jd_title or role_title,
            content=jd_content, source_url=source_url,
        )

        resume = None
        resume_text = ""
        if resume_id:
            resume = get_object_or_404(Resume, pk=resume_id, owner=request.user)
            resume_text = resume.content

        result = compute_match(resume_text, jd_content)

        Application.objects.create(
            owner=request.user, company=company, job_description=job_description,
            resume=resume, role_title=role_title,
            match_score=result["score"], missing_keywords=result["missing_keywords"],
        )
        messages.success(request, f"Application to {company.name} added — match score {result['score']}%.")
        return redirect("dashboard")

    return render(request, "core/application_form.html", {"companies": companies, "resumes": resumes})


@login_required
def application_detail(request, pk):
    application = get_object_or_404(Application, pk=pk, owner=request.user)
    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status in Application.Status.values:
            application.status = new_status
            application.save(update_fields=["status"])
            messages.success(request, "Status updated.")
        return redirect("application-detail", pk=pk)
    return render(request, "core/application_detail.html", {"application": application})


@login_required
def resume_list(request):
    if request.method == "POST":
        Resume.objects.create(
            owner=request.user,
            title=request.POST.get("title", "").strip(),
            content=request.POST.get("content", "").strip(),
            is_default=bool(request.POST.get("is_default")),
        )
        messages.success(request, "Resume saved.")
        return redirect("resume-list")
    resumes = Resume.objects.filter(owner=request.user)
    return render(request, "core/resume_list.html", {"resumes": resumes})
