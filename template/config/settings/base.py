"""Stable facade over the settings chunks in ``base_parts``.

Never edit this module: add or change a chunk in ``base_parts/`` instead.
"""

# ruff: noqa: F401, F403

from .base_parts.apps import *
from .base_parts.common import *
from .base_parts.core import *
from .base_parts.i18n import *
from .base_parts.logging import *
from .base_parts.middleware import *
from .base_parts.rest import *
from .base_parts.security import *
from .base_parts.storage import *
from .base_parts.templates import *
from .base_parts.tripaulx import *
