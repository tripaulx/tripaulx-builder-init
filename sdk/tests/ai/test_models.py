"""Models: unique slugs (even after delete), live-only names, team rules."""

from __future__ import annotations

from django.db import IntegrityError, transaction

from tripaulx.ai.models import Agent, AgentRole, AISettings, Skill, TeamMember
from tripaulx.core.testing import TenantTestCase

from .helpers import new_agent, published_skill


class SlugAndNameTests(TenantTestCase):
    def test_slug_from_name_and_unique_after_delete(self):
        a = new_agent("Document Reviewer")
        assert a.slug == "document-reviewer"
        a.delete()
        b = new_agent("Document Reviewer")
        assert b.slug == "document-reviewer-2"
        assert Agent.all_objects.get(pk=a.pk).deleted_at is not None

    def test_name_unique_among_live_rows_only(self):
        a = new_agent("Ana")
        with self.assertRaises(IntegrityError), transaction.atomic():
            new_agent("ana")
        a.delete()
        new_agent("ANA")

    def test_skill_slug_and_draft(self):
        s = Skill.objects.create(name="Formal style", instructions="x")
        assert s.slug == "formal-style"
        assert not s.is_published and s.has_pending_draft


class TeamTests(TenantTestCase):
    def test_not_a_member_of_its_own_team(self):
        c = new_agent("Coord", role=AgentRole.COORDINATOR)
        with self.assertRaises(IntegrityError), transaction.atomic():
            TeamMember.objects.create(coordinator=c, specialist=c, order=0)

    def test_live_members_skip_deleted_and_inactive_in_order(self):
        c = new_agent("Coord", role=AgentRole.COORDINATOR)
        a, b, d = new_agent("A"), new_agent("B", active=False), new_agent("D")
        TeamMember.objects.create(coordinator=c, specialist=d, order=2)
        TeamMember.objects.create(coordinator=c, specialist=a, order=0)
        TeamMember.objects.create(coordinator=c, specialist=b, order=1)
        d.delete()
        assert [m.specialist.name for m in c.live_members()] == ["A"]


class SkillVersionTests(TenantTestCase):
    def test_published_and_pending_draft(self):
        s = published_skill("Rule", "v1")
        assert s.is_published and not s.has_pending_draft
        s.instructions = "v2"
        assert s.has_pending_draft


class SettingsSingletonTests(TenantTestCase):
    def test_load_creates_and_reuses_one_row(self):
        assert AISettings.load().pk == 1
        AISettings(pk=7).save()
        assert AISettings.objects.count() == 1

    def test_clean_refuses_a_model_outside_the_provider_catalog(self):
        settings = AISettings.load()
        settings.provider = "anthropic"
        settings.model_identifier = "gpt-6.1-sol"
        with self.assertRaises(Exception) as ctx:
            settings.full_clean()
        assert "model_identifier" in str(ctx.exception)
