from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("meshapi", "0009_merge_after_battery"),
    ]

    operations = [
        migrations.AddField(
            model_name="collectorconfig",
            name="enable_req_telemetry",
            field=models.BooleanField(default=False),
        ),
    ]

