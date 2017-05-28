# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-05-27 06:07
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('investor', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='investor',
            name='users',
            field=models.ManyToManyField(blank=True, related_name='investor_set', to=settings.AUTH_USER_MODEL, verbose_name='Users'),
        ),
    ]
