from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="NodeInfo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(db_index=True, max_length=128)),
                ("data", models.JSONField()),
                ("fetched_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
            ],
            options={
                "ordering": ["-fetched_at"],
            },
        ),
        migrations.AddIndex(
            model_name="nodeinfo",
            index=models.Index(fields=["name", "fetched_at"], name="meshapi_node_name_fetch_idx"),
        ),
    ]

