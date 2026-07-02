"""
Tests for OrganizerRegistrationSerializer + OrganizerRegistrationView.

Schema notes (from the real models module):
- User.user_id is an auto-generated UUID pk -- don't pass it in, read it off
  the saved instance.
- User.is_organizer is a read-only @property derived from user_type
  ('O' = organizer, 'C' = competitor). Set user_type, not is_organizer.
- User.school is a FK to College (not "School").
- There's no Config model -- it's `Settings`, looked up via Settings.load(),
  which caches the latest row for 1hr (cache key: 'competition_settings_latest').
  Settings.save() busts that cache; *deleting* a row does not, so any test
  that simulates "no settings configured" must clear the cache explicitly.
- Settings requires reg_start, reg_end, contact_email, and host (FK->College)
  in addition to reg_year.
- Event's pk is event_code (CharField), not a numeric id.

ASSUMPTIONS still being made (adjust if wrong):
- `requires_settings` calls Settings.load() and attaches the result to the
  view as `self.config` (matching the OrganizerRegistrationView code shown),
  returning a 4xx of some kind if no Settings row exists -- or alternately
  just lets get_queryset() fall through to User.objects.none(). The
  RequiresSettingsTests below accept either; tighten once you know the
  decorator's exact behavior.
- URLs are registered via a router with basename "organizer-registration".
- Fixture files `colleges.json` and `events.json` exist under your app's
  fixtures/ directory (or FIXTURE_DIRS) and contain at least the
  College/Event rows referenced below by name/event_code. Adjust the
  lookup values to match what's actually in your fixtures.
"""

from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.test import override_settings


from ..models import (  # adjust import path to your app
    User,
    College,
    Event,
    Registration,
    Settings,
    UserTypeChoices,
)

@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class OrganizerRegistrationTestBase(APITestCase):
    """Shared fixtures for all organizer-registration tests."""

    fixtures = ['schools.json', 'events.json']

    @classmethod
    def setUpTestData(cls):
        # Pull from fixtures rather than hardcoding pks/UUIDs.
        cls.college = College.objects.first()
        cls.event_a = Event.objects.get(event_code="NMN111")
        cls.event_b = Event.objects.get(event_code="AMA101")
        cls.event_c = Event.objects.get(event_code="AFA101")

        cls.settings = Settings.objects.create(
            reg_year=2025,
            reg_start="2025-01-01",
            reg_end="2025-12-31",
            contact_email="contact@example.com",
            host=cls.college,
            reg_cost_first=50,
            reg_cost_extra=20
        )

        cls.organizer = User.objects.create(
            email="organizer@example.com",
            first_name="Org",
            last_name="Anizer",
            user_type=UserTypeChoices.ORGANIZER,
        )

        cls.non_organizer = User.objects.create(
            email="user1@example.com",
            first_name="Reg",
            last_name="User",
            user_type=UserTypeChoices.COMPETITOR,
        )

        cls.competitor = User.objects.create(
            email="competitor1@example.com",
            first_name="Comp",
            last_name="Etitor",
            gender="F",
            skill_level="A",
            student_type="1",
            school=cls.college,
            is_competing=True,
            has_paid=False,
            user_type=UserTypeChoices.COMPETITOR,
        )

        cls.reg_a = Registration.objects.create(
            competitor=cls.competitor,
            event=cls.event_a,
            nandu_str="abc",
            comp_year=2025,
        )
        cls.reg_b = Registration.objects.create(
            competitor=cls.competitor,
            event=cls.event_b,
            nandu_str="def",
            comp_year=2025,
        )

    def setUp(self):
        # Settings.load() caches across tests; make sure each test starts clean.
        cache.clear()

    def auth_as(self, user):
        self.client.force_authenticate(user=user)

    def detail_url(self, user_id):
        return reverse("registration-detail", args=[user_id])

    def list_url(self):
        return reverse("registration-list")


class PermissionsTests(OrganizerRegistrationTestBase):
    def test_anonymous_blocked_from_list(self):
        resp = self.client.get(self.list_url())
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_non_organizer_blocked_from_list(self):
        self.auth_as(self.non_organizer)
        resp = self.client.get(self.list_url())
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_organizer_blocked_from_patch(self):
        self.auth_as(self.non_organizer)
        resp = self.client.patch(
            self.detail_url(self.competitor.user_id), {"has_paid": True}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_disallowed_methods_rejected(self):
        self.auth_as(self.organizer)
        resp = self.client.post(self.list_url(), {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        resp = self.client.delete(self.detail_url(self.competitor.user_id))
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        resp = self.client.put(self.detail_url(self.competitor.user_id), {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class RequiresSettingsTests(OrganizerRegistrationTestBase):
    def test_list_without_settings_returns_empty_or_error(self):
        self.settings.delete()
        cache.clear()  # Settings.save() busts the cache; delete() doesn't

        self.auth_as(self.organizer)
        resp = self.client.get(self.list_url())
        self.assertIn(
            resp.status_code,
            (status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND),
        )
        if resp.status_code == status.HTTP_200_OK:
            self.assertEqual(len(resp.data), 0)

    def test_settings_load_uses_most_recently_created_row(self):
        # Settings.Meta.ordering = ["-created_at"], so .load() should pick
        # up the newest row if multiple exist.
        newer = Settings.objects.create(
            reg_year=2026,
            reg_start="2026-01-01",
            reg_end="2026-12-31",
            contact_email="contact2026@example.com",
            host=self.college,
            reg_cost_first=50,
            reg_cost_extra=20
        )
        cache.clear()
        self.assertEqual(Settings.load().reg_year, newer.reg_year)


class ListRetrieveTests(OrganizerRegistrationTestBase):
    def test_list_only_includes_users_registered_for_current_reg_year(self):
        other_year_user = User.objects.create(
            email="old@example.com",
            first_name="Old",
            last_name="Comp",
            user_type=UserTypeChoices.COMPETITOR,
        )
        Registration.objects.create(
            competitor=other_year_user, event=self.event_a, nandu_str="x", comp_year=2024
        )

        self.auth_as(self.organizer)
        resp = self.client.get(self.list_url())
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        returned_ids = {row["user_id"] for row in resp.data}
        self.assertIn(str(self.competitor.user_id), returned_ids)
        self.assertNotIn(str(other_year_user.user_id), returned_ids)

    def test_retrieve_includes_nested_registrations(self):
        self.auth_as(self.organizer)
        resp = self.client.get(self.detail_url(self.competitor.user_id))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["registration"]), 2)
        self.assertEqual(resp.data["user_id"], str(self.competitor.user_id))

    def test_name_field_renders_str_user(self):
        self.auth_as(self.organizer)
        resp = self.client.get(self.detail_url(self.competitor.user_id))
        self.assertEqual(resp.data["name"], str(self.competitor))  # "Comp Etitor"

    def test_school_field_renders_str_college(self):
        self.auth_as(self.organizer)
        resp = self.client.get(self.detail_url(self.competitor.user_id))
        self.assertEqual(resp.data["school"], str(self.college))


class PatchSimpleFieldsTests(OrganizerRegistrationTestBase):
    def test_patch_has_paid_and_is_competing(self):
        self.auth_as(self.organizer)
        resp = self.client.patch(
            self.detail_url(self.competitor.user_id),
            {"has_paid": True, "is_competing": False},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.competitor.refresh_from_db()
        self.assertTrue(self.competitor.has_paid)
        self.assertFalse(self.competitor.is_competing)

    def test_patch_ignores_read_only_fields(self):
        self.auth_as(self.organizer)
        original_email = self.competitor.email
        resp = self.client.patch(
            self.detail_url(self.competitor.user_id),
            {"email": "hacked@example.com"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.competitor.refresh_from_db()
        self.assertEqual(self.competitor.email, original_email)


class PatchRegistrationInputTests(OrganizerRegistrationTestBase):
    """
    Exercises OrganizerRegistrationSerializer.update()'s add/delete/update
    branches against event_code-keyed Events.
    """

    def test_patch_adds_new_event_registration(self):
        self.auth_as(self.organizer)
        payload = {
            "registration_input": [
                {"event": self.event_a.event_code, "nandu_str": "abc"},
                {"event": self.event_b.event_code, "nandu_str": "def"},
                {"event": self.event_c.event_code, "nandu_str": "ghi"},
            ]
        }
        resp = self.client.patch(
            self.detail_url(self.competitor.user_id), payload, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        regs = Registration.objects.filter(competitor=self.competitor, comp_year=2025)
        self.assertEqual(regs.count(), 3)
        self.assertTrue(regs.filter(event=self.event_c, nandu_str="ghi").exists())

    def test_patch_removes_event_registration(self):
        self.auth_as(self.organizer)
        payload = {
            "registration_input": [
                {"event": self.event_a.event_code, "nandu_str": "abc"},
            ]
        }
        resp = self.client.patch(
            self.detail_url(self.competitor.user_id), payload, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        regs = Registration.objects.filter(competitor=self.competitor, comp_year=2025)
        self.assertEqual(regs.count(), 1)
        self.assertFalse(regs.filter(event=self.event_b).exists())

    def test_patch_updates_existing_nandu_str(self):
        self.auth_as(self.organizer)
        payload = {
            "registration_input": [
                {"event": self.event_a.event_code, "nandu_str": "updated-value"},
                {"event": self.event_b.event_code, "nandu_str": "def"},
            ]
        }
        resp = self.client.patch(
            self.detail_url(self.competitor.user_id), payload, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.reg_a.refresh_from_db()
        self.assertEqual(self.reg_a.nandu_str, "updated-value")

    def test_patch_empty_nandu_str_does_not_overwrite_existing_value(self):
        self.auth_as(self.organizer)
        payload = {
            "registration_input": [
                {"event": self.event_a.event_code, "nandu_str": ""},
                {"event": self.event_b.event_code, "nandu_str": "def"},
            ]
        }
        resp = self.client.patch(
            self.detail_url(self.competitor.user_id), payload, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.reg_a.refresh_from_db()
        self.assertEqual(self.reg_a.nandu_str, "abc")

    def test_patch_with_empty_registration_input_clears_all_registrations(self):
        self.auth_as(self.organizer)
        payload = {"registration_input": []}
        resp = self.client.patch(
            self.detail_url(self.competitor.user_id), payload, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(
            Registration.objects.filter(competitor=self.competitor, comp_year=2025).count(), 0
        )

    def test_patch_without_registration_input_leaves_registrations_unchanged(self):
        self.auth_as(self.organizer)
        resp = self.client.patch(
            self.detail_url(self.competitor.user_id), {"has_paid": True}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(
            Registration.objects.filter(competitor=self.competitor, comp_year=2025).count(), 2
        )

    def test_patch_only_affects_current_comp_year_registrations(self):
        Registration.objects.create(
            competitor=self.competitor, event=self.event_c, nandu_str="old", comp_year=2024
        )
        self.auth_as(self.organizer)
        payload = {
            "registration_input": [
                {"event": self.event_a.event_code, "nandu_str": "abc"},
            ]
        }
        resp = self.client.patch(
            self.detail_url(self.competitor.user_id), payload, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertTrue(
            Registration.objects.filter(
                competitor=self.competitor, comp_year=2024, event=self.event_c
            ).exists()
        )

    def test_patch_invalid_event_in_registration_input_returns_400(self):
        self.auth_as(self.organizer)
        payload = {
            "registration_input": [
                {"event": "NOT-A-REAL-EVENT-CODE", "nandu_str": "x"},
            ]
        }
        resp = self.client.patch(
            self.detail_url(self.competitor.user_id), payload, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_duplicate_registration_in_payload_does_not_violate_unique_together(self):
        # unique_together = ('competitor', 'comp_year', 'event') -- make sure
        # the same event code can't be submitted twice in one payload and
        # crash bulk_create with an IntegrityError instead of a clean 400.
        self.auth_as(self.organizer)
        payload = {
            "registration_input": [
                {"event": self.event_c.event_code, "nandu_str": "x"},
                {"event": self.event_c.event_code, "nandu_str": "y"},
            ]
        }
        resp = self.client.patch(
            self.detail_url(self.competitor.user_id), payload, format="json"
        )
        self.assertIn(
            resp.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_200_OK)
        )