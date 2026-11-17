"""E-mail preview route (404 unless ``DEBUG``).

Mount it in the public URLconf::

    path("__mail/", include("tripaulx.mail.urls")),
"""

from django.urls import path

from .views import preview

app_name = "tpsdk_mail"

urlpatterns = [
    path("<str:name>/", preview, name="preview"),
]
