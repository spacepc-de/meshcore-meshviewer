from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("meshapi", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Contact",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_key", models.CharField(max_length=64, unique=True)),
                ("name", models.CharField(blank=True, default="", max_length=128)),
                ("first_seen", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("last_seen", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
            ],
            options={
                "ordering": ["-last_seen"],
            },
        ),
        migrations.AddIndex(
            model_name="contact",
            index=models.Index(fields=["public_key"], name="meshapi_cont_public_k_idx"),
        ),
        migrations.AddIndex(
            model_name="contact",
            index=models.Index(fields=["last_seen"], name="meshapi_cont_last_seen_idx"),
        ),
        migrations.CreateModel(
            name="ContactTelemetry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fetched_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("adv_name", models.CharField(blank=True, default="", max_length=128)),
                ("last_advert", models.BigIntegerField(blank=True, null=True)),
                ("adv_lat", models.FloatField(blank=True, null=True)),
                ("adv_lon", models.FloatField(blank=True, null=True)),
                ("type", models.IntegerField(blank=True, null=True)),
                ("flags", models.IntegerField(blank=True, null=True)),
                ("out_path_len", models.IntegerField(blank=True, null=True)),
                ("out_path", models.TextField(blank=True, default="")),
                ("lastmod", models.BigIntegerField(blank=True, null=True)),
                ("raw", models.JSONField(default=dict)),
                ("contact", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="telemetry", to="meshapi.contact")),
            ],
            options={
                "ordering": ["-fetched_at"],
            },
        ),
        migrations.AddIndex(
            model_name="contacttelemetry",
            index=models.Index(fields=["contact", "fetched_at"], name="meshapi_tele_contact_fetch_idx"),
        ),
    ]

