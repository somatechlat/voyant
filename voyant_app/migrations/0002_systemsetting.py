from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("voyant_app", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SystemSetting",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("key", models.CharField(db_index=True, max_length=128, unique=True)),
                ("value", models.TextField(blank=True)),
                (
                    "value_type",
                    models.CharField(
                        choices=[
                            ("string", "String"),
                            ("integer", "Integer"),
                            ("float", "Float"),
                            ("boolean", "Boolean"),
                            ("json", "JSON"),
                        ],
                        default="string",
                        max_length=16,
                    ),
                ),
                ("description", models.CharField(blank=True, max_length=512)),
                ("is_secret", models.BooleanField(default=False)),
                ("is_runtime", models.BooleanField(default=False)),
                ("managed_in_db", models.BooleanField(default=True)),
                ("updated_by", models.CharField(blank=True, max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["managed_in_db", "is_secret", "is_runtime"],
                        name="voyant_app__managed_28bfb8_idx",
                    )
                ],
            },
        ),
    ]
