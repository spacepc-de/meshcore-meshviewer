from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("meshapi", "0011_merge_0010s"),
    ]

    operations = [
        migrations.AddField(
            model_name="collectorconfig",
            name="enable_req_status",
            field=models.BooleanField(default=True),
        ),
    ]
