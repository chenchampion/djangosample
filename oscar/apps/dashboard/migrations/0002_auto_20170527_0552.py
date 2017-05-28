# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-05-27 05:52
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eventtype',
            name='related_group',
            field=models.ManyToManyField(blank=True, related_name='related_group1', to='auth.Group'),
        ),
        migrations.AlterField(
            model_name='eventtype',
            name='users',
            field=models.ManyToManyField(blank=True, related_name='user_projects1', to=settings.AUTH_USER_MODEL),
        ),
    ]