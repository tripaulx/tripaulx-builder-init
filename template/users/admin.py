"""Admin registration of the project user."""

from django.contrib import admin
from tripaulx.accounts.admin import TripaulxUserAdmin

from .models import User

admin.site.register(User, TripaulxUserAdmin)
