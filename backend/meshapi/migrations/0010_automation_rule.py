from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("meshapi", "0009_merge_after_battery"),
    ]

    operations = [
        migrations.CreateModel(
            name="AutomationRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("enabled", models.BooleanField(db_index=True, default=True)),
                ("name", models.CharField(max_length=128)),
                ("description", models.TextField(blank=True, default="")),
                ("match_type", models.CharField(choices=[("equals", "equals"), ("prefix", "prefix"), ("contains", "contains"), ("regex", "regex")], default="prefix", max_length=16)),
                ("pattern", models.CharField(max_length=256)),
                ("case_sensitive", models.BooleanField(default=False)),
                ("only_incoming", models.BooleanField(default=True)),
                ("from_name", models.CharField(blank=True, default="", max_length=128)),
                ("from_public_key", models.CharField(blank=True, default="", max_length=64)),
                ("action_type", models.CharField(choices=[("autoresponse", "autoresponse"), ("mqtt", "mqtt")], max_length=32)),
                ("response_text", models.TextField(blank=True, default="")),
                ("mqtt_topic", models.CharField(blank=True, default="", max_length=255)),
                ("mqtt_payload", models.TextField(blank=True, default="")),
                ("priority", models.IntegerField(db_index=True, default=0)),
                ("stop_processing", models.BooleanField(default=True)),
                ("cooldown_seconds", models.IntegerField(default=0)),
                ("last_triggered_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-enabled", "-priority", "name"],
            },
        ),
        migrations.AddIndex(
            model_name="automationrule",
            index=models.Index(fields=["enabled", "priority"], name="meshapi_aut_enabled_prio_idx"),
        ),
    ]

