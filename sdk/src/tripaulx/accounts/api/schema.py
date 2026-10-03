"""OpenAPI (drf-spectacular) glue for the accounts API.

Imported by ``AccountsConfig.ready`` so the authentication extension is
registered before any schema is generated.
"""

from __future__ import annotations

from drf_spectacular.contrib.rest_framework_simplejwt import SimpleJWTScheme
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema


class TenantJWTScheme(SimpleJWTScheme):
    """Describe ``TenantJWTAuthentication`` as a plain bearer JWT."""

    target_class = "tripaulx.accounts.api.authentication.TenantJWTAuthentication"
    name = "jwtAuth"


#: For views without a request serializer that answer free-form JSON.
untyped = extend_schema(request=None, responses=OpenApiTypes.OBJECT)
