from django.db import migrations, models
import django.utils.timezone
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("meshapi", "0003_collector_config"),
    ]

    operations = [
        migrations.CreateModel(
            name="Message",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(blank=True, default="", max_length=128)),
                ("public_key", models.CharField(blank=True, max_length=64, null=True)),
                ("direction", models.CharField(choices=[("in", "in"), ("out", "out")], max_length=3)),
                ("text", models.TextField()),
                ("ts", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("raw", models.TextField(blank=True, default="")),
                ("contact", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="messages", to="meshapi.contact")),
            ],
            options={
                "ordering": ["-ts"],
            },
        ),
        migrations.AddIndex(
            model_name="message",
            index=models.Index(fields=["ts"], name="meshapi_mess_ts_idx"),
        ),
        migrations.AddIndex(
            model_name="message",
            index=models.Index(fields=["public_key"], name="meshapi_mess_pubkey_idx"),
        ),
    ]

