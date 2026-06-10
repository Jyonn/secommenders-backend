# Generated manually for Secommenders backend metadata evolution.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('evaluation', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='evaluation',
            name='compile_prepare_id',
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.AddField(
            model_name='evaluation',
            name='data_name',
            field=models.CharField(blank=True, db_index=True, max_length=128),
        ),
        migrations.AddField(
            model_name='evaluation',
            name='hash_coder',
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name='evaluation',
            name='model_name',
            field=models.CharField(blank=True, db_index=True, max_length=128),
        ),
        migrations.AddField(
            model_name='evaluation',
            name='plan_name',
            field=models.CharField(blank=True, db_index=True, max_length=128),
        ),
        migrations.AddField(
            model_name='evaluation',
            name='repr_combine',
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name='evaluation',
            name='repr_source_model',
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name='evaluation',
            name='repr_type',
            field=models.CharField(blank=True, db_index=True, max_length=128),
        ),
        migrations.AddField(
            model_name='evaluation',
            name='run_id',
            field=models.CharField(blank=True, db_index=True, max_length=128),
        ),
        migrations.AddField(
            model_name='evaluation',
            name='sid_coder',
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name='evaluation',
            name='task_type',
            field=models.CharField(blank=True, db_index=True, max_length=128),
        ),
        migrations.AddField(
            model_name='experiment',
            name='best_epoch',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='experiment',
            name='best_valid_metric',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='experiment',
            name='main_metric',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name='experiment',
            name='test_metric_name',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name='experiment',
            name='world_size',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
