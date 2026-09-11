from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ontology", "0003_actiontype_requires_approval"),
    ]

    operations = [
        migrations.AddField(
            model_name="objecttype",
            name="backing_dataset",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "Fully-qualified Iceberg table name (schema.table) that stores "
                    "instances of this object type. Used by the Ontology Query Engine "
                    "to translate semantic queries into Trino SQL against the lakehouse."
                ),
                max_length=512,
            ),
        ),
        migrations.AddField(
            model_name="objecttype",
            name="primary_key_column",
            field=models.CharField(
                blank=True,
                default="id",
                help_text=(
                    "Name of the column in the backing dataset that serves as the "
                    "primary key. Used for cursor-based (keyset) pagination."
                ),
                max_length=255,
            ),
        ),
    ]
