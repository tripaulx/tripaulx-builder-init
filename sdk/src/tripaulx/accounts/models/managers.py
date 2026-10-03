"""Manager for e-mail based users (no username)."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext as _

from .roles import Role


class UserManager(BaseUserManager):
    """Create users identified by their e-mail address."""

    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra: Any) -> Any:
        """Normalize the e-mail, hash the password and save the user."""
        if not email:
            raise ValueError(_("An e-mail address is required."))
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra: Any) -> Any:
        """Create a regular workspace member."""
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(
        self, email: str, password: str | None = None, **extra: Any
    ) -> Any:
        """Create a superuser: staff, verified e-mail and workspace owner."""
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_active", True)
        extra.setdefault("email_verified", True)
        extra.setdefault("role", Role.OWNER)
        if extra["is_staff"] is not True or extra["is_superuser"] is not True:
            raise ValueError(_("A superuser needs is_staff and is_superuser."))
        return self._create_user(email, password, **extra)
