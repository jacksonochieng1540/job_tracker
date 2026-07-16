from django.contrib import admin
from .models import Company, Resume, JobDescription, Application


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at")
    search_fields = ("name",)


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "is_default", "created_at")
    list_filter = ("is_default",)


@admin.register(JobDescription)
class JobDescriptionAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "created_at")


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("role_title", "company", "owner", "status", "match_score", "updated_at")
    list_filter = ("status",)
    search_fields = ("role_title", "company__name")
