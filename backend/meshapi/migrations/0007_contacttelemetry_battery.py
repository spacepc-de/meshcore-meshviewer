from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("meshapi", "0006_contacttelemetry_quality"),
    ]

    operations = [
        migrations.AddField(
            model_name="contacttelemetry",
            name="battery_mv",
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="contacttelemetry",
            name="battery_percent",
            field=models.FloatField(null=True, blank=True),
        ),
    ]

