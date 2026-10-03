"""Pieces shared by the AI views."""

#: UUID in URLs.
UUID_URL = "[0-9a-fA-F-]{36}"

#: No PUT: clients save with partial PATCH, and a PUT without ``team`` would
#: wipe the team of someone who only meant to change the description.
METHODS_WITHOUT_PUT = ["get", "post", "patch", "delete", "head", "options"]
