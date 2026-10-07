"""Admin of agents and skills (including soft-deleted rows)."""

from __future__ import annotations

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from tripaulx.ai.models import Agent, AgentSkill, Skill, SkillVersion, TeamMember
from tripaulx.ai.services import skills as skill_service
from tripaulx.core.admin_scope import WorkspaceSchemaAdmin

AUDIT = ("id", "created_by", "created_at", "updated_at", "deleted_at")


class TeamMemberInline(admin.TabularInline):
    """Team of a coordinator."""

    model = TeamMember
    fk_name = "coordinator"
    fields = ("specialist", "order")
    extra = 0


class AgentSkillInline(admin.TabularInline):
    """Skills attached to an agent."""

    model = AgentSkill
    fields = ("skill", "order", "required")
    extra = 0


@admin.register(Agent)
class AgentAdmin(WorkspaceSchemaAdmin, admin.ModelAdmin):
    """Agents with team and skills inline."""

    list_display = ("name", "slug", "role", "model_identifier", "active", "deleted_at")
    list_filter = ("role", "active")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("slug", *AUDIT)
    inlines = (TeamMemberInline, AgentSkillInline)
    fieldsets = (
        (None, {"fields": ("name", "slug", "description", "role", "active", "order")}),
        (_("Prompt"), {"fields": ("instructions", "input_template", "output_schema")}),
        (
            _("Model"),
            {
                "fields": (
                    "model_identifier",
                    "effort",
                    "verbosity",
                    "temperature",
                    "max_output_tokens",
                    "web_search",
                    "web_search_domains",
                )
            },
        ),
        (_("Audit"), {"fields": AUDIT}),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Include soft-deleted agents."""
        return Agent.all_objects.all()


class SkillVersionInline(admin.TabularInline):
    """Published versions (read-only)."""

    model = SkillVersion
    fields = ("number", "note", "published_at", "published_by_label")
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(
        self, request: HttpRequest, obj: Skill | None = None
    ) -> bool:
        """Versions come from publishing only."""
        return False


@admin.register(Skill)
class SkillAdmin(WorkspaceSchemaAdmin, admin.ModelAdmin):
    """Skills: draft, versions and the publish action."""

    list_display = ("name", "slug", "published_version", "active", "deleted_at")
    list_filter = ("active",)
    search_fields = ("name", "slug", "description")
    readonly_fields = ("slug", "published_version", *AUDIT)
    inlines = (SkillVersionInline,)
    actions = ("publish_draft",)
    fieldsets = (
        (None, {"fields": ("name", "slug", "description", "active", "order")}),
        (_("Instructions (draft)"), {"fields": ("instructions", "published_version")}),
        (
            _("Model and limits"),
            {"fields": ("model_identifier", "effort", "max_output_tokens")},
        ),
        (_("Audit"), {"fields": AUDIT}),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Include soft-deleted skills."""
        return Skill.all_objects.select_related("published_version")

    @admin.action(description=_("Publish the draft as a new version"))
    def publish_draft(self, request: HttpRequest, queryset: QuerySet) -> None:
        """Publish each selected skill, reporting per skill."""
        for skill in queryset:
            try:
                version = skill_service.publish(
                    skill, by=request.user, note=gettext("Published from the admin.")
                )
            except skill_service.NothingToPublish as exc:
                self.message_user(
                    request, f"{skill.name}: {exc}", level=messages.WARNING
                )
            else:
                self.message_user(
                    request,
                    gettext("%(name)s: version %(number)s published.")
                    % {"name": skill.name, "number": version.number},
                )
