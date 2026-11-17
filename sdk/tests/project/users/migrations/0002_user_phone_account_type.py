"""Add the project-specific fields used by the registration tests."""

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("users", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="account_type",
            field=models.CharField(blank=True, max_length=16),
        ),
        migrations.AddField(
            model_name="user",
            name="phone",
            field=models.CharField(
                blank=True,
                max_length=20,
                validators=[django.core.validators.RegexValidator("^\\+?[0-9]{8,15}$")],
            ),
        ),
    ]
