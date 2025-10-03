from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("meshapi", "0005_message_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="MQTTConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("server", models.CharField(blank=True, default="", max_length=255)),
                ("port", models.IntegerField(default=1883)),
                ("username", models.CharField(blank=True, default="", max_length=255)),
                ("password", models.CharField(blank=True, default="", max_length=255)),
                ("use_tls", models.BooleanField(default=False)),
                ("default_community", models.CharField(blank=True, default="", max_length=255)),
            ],
        ),
    ]

