# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-05-27 05:49
from __future__ import unicode_literals

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('bankaccounts', '0002_bankaccount_owners'),
    ]

    operations = [
        migrations.CreateModel(
            name='TaskExpense',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(default=datetime.date.today, verbose_name='Date')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Amount')),
                ('currency', models.CharField(editable=False, max_length=3, verbose_name='Currency')),
                ('payment_method', models.CharField(choices=[(b'credit_card', 'Credit card'), (b'cash', 'Cash'), (b'transfer', 'Transfer'), (b'transfer_internal', 'Transfer internal'), (b'check', 'Check')], default=b'credit_card', max_length=32, verbose_name='Payment method')),
                ('memo', models.TextField(blank=True, verbose_name='Memo')),
                ('bankaccount', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='taskexpenses', to='bankaccounts.BankAccount')),
            ],
        ),
    ]