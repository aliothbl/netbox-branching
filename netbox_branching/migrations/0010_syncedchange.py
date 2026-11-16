import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0011_move_objectchange'),
        ('netbox_branching', '0009_changediff_last_updated_auto_now'),
    ]

    operations = [
        migrations.AddField(
            model_name='branch',
            name='sync_watermark',
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        migrations.CreateModel(
            name='SyncedChange',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                (
                    'branch',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='synced_changes',
                        to='netbox_branching.branch',
                    ),
                ),
                (
                    'change',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='sync_applications',
                        to='core.objectchange',
                    ),
                ),
            ],
            options={
                'verbose_name': 'synced change',
                'verbose_name_plural': 'synced changes',
                'ordering': ('branch', 'change'),
                'constraints': [
                    models.UniqueConstraint(fields=('branch', 'change'), name='netbox_branching_syncedchange_unique')
                ],
            },
        ),
    ]
