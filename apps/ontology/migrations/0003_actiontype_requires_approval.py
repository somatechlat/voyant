from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ontology", "0002_actionexecution"),
    ]

    operations = [
        migrations.AddField(
            model_name="actiontype",
            name="requires_approval",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="If true, executing this action creates an approval request instead of executing immediately",
            ),
        ),
    ]
