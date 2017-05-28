from datetime import date
from decimal import Decimal
from django.db import models
from mymoney.apps.bankaccounts.models import BankAccount

from django.utils.translation import ugettext_lazy as _
from oscar.apps.dashboard.project.models import Task, Project
from oscar.apps.dashboard.project.helpers import get_project
from django.db.models.query import QuerySet
from itertools import chain

class TaskExpenseManager(models.Manager):

    def get_task_expense(self, request, project_name):
        project = get_project(request, project_name)
        group_tasks = project.task_set.all()
        expense_set = list()
        for task in group_tasks:
            expense_set = chain(expense_set, task.taskexpenses.all())

        return expense_set

    def delete_orphans(self):
        """
        Delete bank account which have no more owners.
        """
        self.filter(owners__isnull=True).delete()

class TaskExpense(models.Model):

    PAYMENT_METHOD_CREDIT_CARD = 'credit_card'
    PAYMENT_METHOD_CASH = 'cash'
    PAYMENT_METHOD_TRANSFER = 'transfer'
    PAYMENT_METHOD_TRANSFER_INTERNAL = 'transfer_internal'
    PAYMENT_METHOD_CHECK = 'check'

    PAYMENT_METHODS = (
        (PAYMENT_METHOD_CREDIT_CARD, _('Credit card')),
        (PAYMENT_METHOD_CASH, _('Cash')),
        (PAYMENT_METHOD_TRANSFER, _('Transfer')),
        (PAYMENT_METHOD_TRANSFER_INTERNAL, _('Transfer internal')),
        (PAYMENT_METHOD_CHECK, _('Check')),
    )

    bankaccount = models.ForeignKey(
        BankAccount,
        related_name='%(class)ss',
        on_delete=models.CASCADE,
    )
    date = models.DateField(default=date.today, verbose_name=_('Date'))
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Amount'),
    )
    currency = models.CharField(
        max_length=3,
        verbose_name=_('Currency'),
        editable=False,
    )

    task = models.ForeignKey(
        Task,
        blank=True,
        null=True,
        verbose_name=_('Task'),
    )

    payment_method = models.CharField(
        max_length=32,
        choices=PAYMENT_METHODS,
        default=PAYMENT_METHOD_CREDIT_CARD,
        verbose_name=_('Payment method'),
    )
    memo = models.TextField(blank=True, verbose_name=_('Memo'))

    objects = TaskExpenseManager()

    def __str__(self):
        return self.label