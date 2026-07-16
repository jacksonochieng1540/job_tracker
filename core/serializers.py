from rest_framework import serializers
from .models import Company, Resume, JobDescription, Application


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "name", "website", "notes", "created_at"]
        read_only_fields = ["id", "created_at"]


class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = ["id", "title", "content", "file", "is_default", "created_at"]
        read_only_fields = ["id", "created_at"]


class JobDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobDescription
        fields = ["id", "title", "content", "source_url", "created_at"]
        read_only_fields = ["id", "created_at"]


class ApplicationSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    job_description_title = serializers.CharField(source="job_description.title", read_only=True)

    class Meta:
        model = Application
        fields = [
            "id", "company", "company_name", "job_description", "job_description_title",
            "resume", "role_title", "status", "applied_on", "notes",
            "match_score", "missing_keywords", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "match_score", "missing_keywords", "created_at", "updated_at"]


class MatchRequestSerializer(serializers.Serializer):
    """Input for the standalone POST /api/match/ endpoint (no Application needed)."""
    resume_text = serializers.CharField()
    jd_text = serializers.CharField()


class MatchResultSerializer(serializers.Serializer):
    score = serializers.FloatField()
    missing_keywords = serializers.ListField(child=serializers.CharField())
