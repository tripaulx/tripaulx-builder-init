"""Concrete user, as a generated project declares it, plus two own fields."""

from django.core.validators import RegexValidator
from django.db import models

from tripaulx.accounts.models import AbstractTripaulxUser


class User(AbstractTripaulxUser):
    """Project user; ``phone`` and ``account_type`` exercise registration."""

    phone = models.CharField(
        max_length=20, blank=True, validators=[RegexValidator(r"^\+?[0-9]{8,15}$")]
    )
    account_type = models.CharField(max_length=16, blank=True)
