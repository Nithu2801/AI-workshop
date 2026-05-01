# Generated for uploaded bike images.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rentals", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="bike",
            name="image",
            field=models.ImageField(blank=True, upload_to="bikes/"),
        ),
    ]
