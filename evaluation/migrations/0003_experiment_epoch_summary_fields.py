# Generated manually for Secommenders backend epoch log summaries.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('evaluation', '0002_evaluation_metadata_fields_experiment_summary_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='experiment',
            name='avg_eval_epoch_seconds',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='experiment',
            name='avg_train_epoch_seconds',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='experiment',
            name='epoch_summary',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='experiment',
            name='log_best_epoch',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='experiment',
            name='trained_epochs',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
