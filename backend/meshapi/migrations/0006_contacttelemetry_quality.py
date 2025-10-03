from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("meshapi", "0005_message_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="contacttelemetry",
            name="rssi",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="contacttelemetry",
            name="snr",
            field=models.FloatField(blank=True, null=True),
        ),
    ]

