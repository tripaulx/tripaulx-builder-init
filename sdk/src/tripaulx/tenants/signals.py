"""Signals sent by the tenants app.

- ``workspace_created``: :func:`tripaulx.tenants.services.provisioning.
  provision_workspace` created a workspace, its schema, its domain and ran its
  setup (``workspace``, ``domain``, ``result``: what the setup returned, e.g.
  the owner created by signup). Sent after the transaction commits.
"""

from django.dispatch import Signal

workspace_created = Signal()
