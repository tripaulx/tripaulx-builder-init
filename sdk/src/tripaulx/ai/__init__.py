"""AI providers, agents, skills and usage events for each workspace.

Two Django apps live here:

- ``tripaulx.ai.catalog`` (shared, label ``tpsdk_ai_catalog``): the model
  catalog with prices, in the public schema.
- ``tripaulx.ai`` (tenant, label ``tpsdk_ai``): settings, keys, agents,
  skills and events of each workspace.
"""
