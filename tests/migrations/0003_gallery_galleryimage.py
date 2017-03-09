# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-03-09 16:13
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import modelcluster.fields


class Migration(migrations.Migration):

    dependencies = [
        ('tests', '0002_add_m2m_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='Gallery',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='GalleryImage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.FileField(upload_to='')),
                ('gallery', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='tests.Gallery')),
            ],
        ),
    ]
