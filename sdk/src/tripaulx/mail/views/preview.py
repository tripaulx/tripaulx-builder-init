"""DEBUG-only preview of the e-mail templates in the browser."""

from __future__ import annotations

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from django.utils import translation
from django.views.decorators.http import require_GET

from ..services import render_mail, sample_context, sample_names


@require_GET
def preview(request: HttpRequest, name: str) -> HttpResponse:
    """Render ``name`` with sample data: ``?lang=pt-br&format=html|txt``.

    Answers 404 unless ``DEBUG`` is on and ``name`` has a registered sample.
    """
    if not settings.DEBUG or name not in sample_names():
        raise Http404
    language = request.GET.get("lang") or settings.LANGUAGE_CODE
    with translation.override(language):
        text, html = render_mail(name, sample_context(name))
    if request.GET.get("format") == "txt":
        return HttpResponse(text, content_type="text/plain; charset=utf-8")
    return HttpResponse(html)
