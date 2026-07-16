from django.conf import settings
from django.db import models
from django.urls import reverse


class Company(models.Model):
    """A company the user is tracking applications against."""
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="companies")
    name = models.CharField(max_length=200)
    website = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("owner", "name")
        verbose_name_plural = "companies"

    def __str__(self):
        return self.name


class Resume(models.Model):
    """
    A version of the user's CV, stored as plain text so it can be embedded
    and compared against job descriptions. Users can keep several versions
    (e.g. 'Backend-focused', 'Data-focused') and pick which one to match.
    """
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="resumes")
    title = models.CharField(max_length=150, help_text="e.g. 'Backend Engineer CV - 2026'")
    content = models.TextField(help_text="Paste the plain-text content of your CV / key bullet points here.")
    file = models.FileField(upload_to="resumes/", blank=True, null=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Only one default resume per user at a time
        if self.is_default:
            Resume.objects.filter(owner=self.owner, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class JobDescription(models.Model):
    """The job posting text pasted in by the user for a given application."""
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="job_descriptions")
    title = models.CharField(max_length=200)
    content = models.TextField()
    source_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Application(models.Model):
    """
    One job application: links a Company + JobDescription + the Resume used,
    tracks its pipeline status, and stores the computed match score/keywords.
    """

    class Status(models.TextChoices):
        SAVED = "SAVED", "Saved"
        APPLIED = "APPLIED", "Applied"
        INTERVIEW = "INTERVIEW", "Interview"
        OFFER = "OFFER", "Offer"
        REJECTED = "REJECTED", "Rejected"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="applications")
    job_description = models.OneToOneField(JobDescription, on_delete=models.CASCADE, related_name="application")
    resume = models.ForeignKey(Resume, on_delete=models.SET_NULL, null=True, blank=True, related_name="applications")

    role_title = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SAVED)
    applied_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    match_score = models.FloatField(null=True, blank=True, help_text="0-100 similarity between resume and JD")
    missing_keywords = models.JSONField(default=list, blank=True, help_text="Terms in the JD not found in the resume")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.role_title} @ {self.company.name}"

    def get_absolute_url(self):
        return reverse("application-detail", kwargs={"pk": self.pk})
