from datetime import timedelta
from celery import current_app
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import BaseCommand, CommandError, call_command
from django.utils import timezone
from rest_framework.test import APIClient

from apps.journals.models import Journal, JournalStaff
from apps.notifications.models import EmailLog
from apps.submissions.models.models import Submission
from apps.users.models import CustomUser, Role


class Command(BaseCommand):
    help = "Run an end-to-end API smoke flow and assert EmailLog rows for workflow notifications."

    def handle(self, *args, **options):
        started_at = timezone.now()

        # Keep Celery and email local/synchronous so API actions produce EmailLog rows immediately.
        current_app.conf.task_always_eager = True
        current_app.conf.task_eager_propagates = True
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

        self.stdout.write(self.style.NOTICE("Seeding email templates..."))
        call_command("create_email_templates")

        suffix = timezone.now().strftime("%Y%m%d%H%M%S")
        editor_role, _ = Role.objects.get_or_create(
            name="EDITOR",
            defaults={"description": "Editor role for smoke run"},
        )

        editor_user = self._create_user_with_role(
            email=f"smoke.editor.{suffix}@example.com",
            first_name="Smoke",
            last_name="Editor",
            role=editor_role,
            is_staff=True,
            is_superuser=True,
        )
        author_user = self._create_user_with_role(
            email=f"smoke.author.{suffix}@example.com",
            first_name="Smoke",
            last_name="Author",
            role=editor_role,
        )
        copyeditor_user = self._create_user_with_role(
            email=f"smoke.copyeditor.{suffix}@example.com",
            first_name="Smoke",
            last_name="Copyeditor",
            role=editor_role,
        )
        production_user = self._create_user_with_role(
            email=f"smoke.production.{suffix}@example.com",
            first_name="Smoke",
            last_name="Production",
            role=editor_role,
        )

        journal = Journal.objects.create(
            title=f"Smoke Journal {suffix}",
            short_name=f"SMK{suffix[-8:]}",
            contact_email=editor_user.email,
            main_contact_email=editor_user.email,
        )
        JournalStaff.objects.get_or_create(
            journal=journal,
            profile=editor_user.profile,
            role="MANAGING_EDITOR",
            defaults={"is_active": True},
        )

        submission = Submission.objects.create(
            journal=journal,
            title=f"Smoke Submission {suffix}",
            abstract="Smoke test abstract",
            corresponding_author=author_user.profile,
            status="ACCEPTED",
        )

        client = APIClient()
        client.force_authenticate(user=editor_user)
        due_date = (timezone.now() + timedelta(days=7)).isoformat()

        self.stdout.write(self.style.NOTICE("1) Creating copyediting assignment via API..."))
        copyediting_resp = client.post(
            "/api/v1/submissions/copyediting/assignments/",
            {
                "submission": str(submission.id),
                "copyeditor_id": str(copyeditor_user.profile.id),
                "due_date": due_date,
                "instructions": "Smoke: copyedit this manuscript.",
            },
            format="json",
        )
        self._assert_response(copyediting_resp, 201, "create copyediting assignment")
        copyediting_id = copyediting_resp.data["id"]

        self.stdout.write(self.style.NOTICE("2) Starting copyediting via API action..."))
        copyediting_start_resp = client.post(
            f"/api/v1/submissions/copyediting/assignments/{copyediting_id}/start/",
            {},
            format="json",
        )
        self._assert_response(copyediting_start_resp, 200, "start copyediting assignment")

        self.stdout.write(self.style.NOTICE("3) Creating production assignment via API..."))
        production_resp = client.post(
            "/api/v1/submissions/production/assignments/",
            {
                "submission": str(submission.id),
                "production_assistant_id": str(production_user.profile.id),
                "due_date": due_date,
                "instructions": "Smoke: create galley and publish.",
            },
            format="json",
        )
        self._assert_response(production_resp, 201, "create production assignment")
        production_id = production_resp.data["id"]

        self.stdout.write(self.style.NOTICE("4) Starting production via API action..."))
        production_start_resp = client.post(
            f"/api/v1/submissions/production/assignments/{production_id}/start/",
            {},
            format="json",
        )
        self._assert_response(production_start_resp, 200, "start production assignment")

        self.stdout.write(self.style.NOTICE("5) Uploading, approving, and publishing galley via API..."))
        upload = SimpleUploadedFile("smoke-galley.pdf", b"%PDF-1.4 smoke", content_type="application/pdf")
        production_file_resp = client.post(
            "/api/v1/submissions/production/files/",
            {
                "assignment": str(production_id),
                "submission": str(submission.id),
                "file_type": "GALLEY",
                "galley_format": "PDF",
                "label": "Smoke PDF",
                "description": "Smoke galley file",
                "file": upload,
            },
            format="multipart",
        )
        self._assert_response(production_file_resp, 201, "upload production galley")
        production_file_id = production_file_resp.data["id"]

        approve_resp = client.post(
            f"/api/v1/submissions/production/files/{production_file_id}/approve/",
            {},
            format="json",
        )
        self._assert_response(approve_resp, 200, "approve production galley")

        publish_resp = client.post(
            f"/api/v1/submissions/production/files/{production_file_id}/publish/",
            {},
            format="json",
        )
        self._assert_response(publish_resp, 200, "publish production galley")

        expected_templates = [
            "COPYEDITING_ASSIGNED",
            "COPYEDITING_EDITORIAL_ASSIGNMENT",
            "COPYEDITING_REQUEST",
            "COPYEDITING_STARTED",
            "PRODUCTION_ASSIGNED",
            "PRODUCTION_STARTED",
            "GALLEY_PUBLISHED",
            "SUBMISSION_PRODUCTION_PROOFREADING",
        ]

        logs = EmailLog.objects.filter(
            created_at__gte=started_at,
            template_type__in=expected_templates,
        )
        counts = {
            template: logs.filter(template_type=template).count()
            for template in expected_templates
        }
        missing = [template for template, count in counts.items() if count == 0]

        self.stdout.write("\nEmailLog counts:")
        for template in expected_templates:
            self.stdout.write(f"- {template}: {counts[template]}")

        if missing:
            raise CommandError(
                "Smoke run completed API actions, but missing EmailLog templates: "
                + ", ".join(missing)
            )

        self.stdout.write(self.style.SUCCESS("\nSmoke run passed: API actions executed and all expected EmailLog rows were created."))

    def _create_user_with_role(self, email, first_name, last_name, role, is_staff=False, is_superuser=False):
        user = CustomUser.objects.create_user(
            email=email,
            password="SmokePass123!",
            first_name=first_name,
            last_name=last_name,
            is_staff=is_staff,
            is_superuser=is_superuser,
        )
        user.profile.roles.add(role)
        return user

    def _assert_response(self, response, expected_status, step):
        if response.status_code != expected_status:
            raise CommandError(
                f"API smoke step failed: {step}. "
                f"Expected HTTP {expected_status}, got {response.status_code}. Response: {getattr(response, 'data', response.content)}"
            )
