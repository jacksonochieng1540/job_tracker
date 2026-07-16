from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .matching import compute_match
from .models import Company, Resume, JobDescription, Application


class MatchingEngineTests(TestCase):
    def test_empty_inputs_return_zero_score(self):
        result = compute_match("", "some jd text")
        self.assertEqual(result["score"], 0.0)
        self.assertEqual(result["missing_keywords"], [])

    def test_identical_text_scores_high(self):
        text = "Python Django REST API PostgreSQL Docker Kubernetes"
        result = compute_match(text, text)
        self.assertGreater(result["score"], 90)

    def test_stronger_overlap_scores_higher_than_weak_overlap(self):
        jd = "Backend Engineer needed with Python, Django, PostgreSQL and Docker experience."
        weak_resume = "Chef with restaurant management experience."
        strong_resume = "Backend engineer skilled in Python, Django, PostgreSQL, and Docker."

        weak = compute_match(weak_resume, jd)
        strong = compute_match(strong_resume, jd)
        self.assertGreater(strong["score"], weak["score"])

    def test_missing_keywords_excludes_covered_terms(self):
        jd = "Must know Kubernetes and Terraform."
        resume = "Experienced with Kubernetes clusters in production."
        result = compute_match(resume, jd)
        self.assertIn("terraform", result["missing_keywords"])
        self.assertNotIn("kubernetes", result["missing_keywords"])


class ApplicationFlowTests(TestCase):
    """Smoke tests for the owner-scoping and dashboard views."""

    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="testpass123")
        self.other_user = User.objects.create_user(username="other", password="testpass123")
        self.client.login(username="tester", password="testpass123")

    def test_dashboard_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)  # redirected to login

    def test_users_cannot_see_each_others_applications(self):
        company = Company.objects.create(owner=self.other_user, name="Other Co")
        jd = JobDescription.objects.create(owner=self.other_user, title="Role", content="Some JD text")
        Application.objects.create(owner=self.other_user, company=company, job_description=jd, role_title="Role")

        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Other Co")

    def test_creating_application_computes_match_score(self):
        Resume.objects.create(
            owner=self.user, title="My CV",
            content="Python Django REST API PostgreSQL", is_default=True,
        )
        response = self.client.post(reverse("application-create"), {
            "role_title": "Backend Engineer",
            "new_company_name": "Acme",
            "jd_title": "Backend role",
            "jd_content": "Looking for Python Django PostgreSQL engineer",
            "resume": Resume.objects.first().id,
        })
        self.assertEqual(response.status_code, 302)
        application = Application.objects.get(role_title="Backend Engineer")
        self.assertIsNotNone(application.match_score)
        self.assertGreater(application.match_score, 0)
