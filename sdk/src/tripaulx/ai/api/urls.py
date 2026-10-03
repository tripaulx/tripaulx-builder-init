"""Routes of the AI API; projects mount them at ``api/v1/ai/`` (workspaces).

Singletons and id-less actions are plain paths; agents, skills and events are
resources with ids, served by the router.
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AgentViewSet,
    AIEventViewSet,
    AIKeyView,
    AISettingsView,
    DashboardView,
    ExecutionView,
    ProbeView,
    ProvidersView,
    SkillViewSet,
)

app_name = "tpsdk_ai"

router = DefaultRouter()
router.include_root_view = False
router.register("agents", AgentViewSet, basename="agent")
router.register("skills", SkillViewSet, basename="skill")
router.register("events", AIEventViewSet, basename="event")

urlpatterns = [
    path("settings/", AISettingsView.as_view(), name="settings"),
    path("key/", AIKeyView.as_view(), name="key"),
    path("providers/", ProvidersView.as_view(), name="providers"),
    # POST: the call has an effect elsewhere (it spends the workspace's
    # tokens), and a GET with effects is what browser prefetch fires alone.
    path("test/", ProbeView.as_view(), name="test"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("executions/<str:task_id>/", ExecutionView.as_view(), name="execution"),
    *router.urls,
]
