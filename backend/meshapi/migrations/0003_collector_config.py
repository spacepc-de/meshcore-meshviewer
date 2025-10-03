from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("meshapi", "0002_contact_telemetry"),
    ]

    operations = [
        migrations.CreateModel(
            name="CollectorConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("interval_seconds", models.IntegerField(default=300)),
            ],
        ),
    ]

