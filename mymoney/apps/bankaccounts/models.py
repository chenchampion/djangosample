from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from mymoney.mymoneycore.utils.currencies import get_currencies
from oscar.apps.dashboard.project.models import Project

class BankAccountManager(models.Manager):

    def get_user_bankaccounts(self, user):

        if not hasattr(user, '_cache_bankaccounts'):
            user._cache_bankaccounts = user.bankaccounts.order_by('label')

        return user._cache_bankaccounts

    def delete_orphans(self):
        """
        Delete bank account which have no more owners.
        """
        self.filter(owners__isnull=True).delete()


class BankAccount(models.Model):

    label = models.CharField(max_length=255, verbose_name=_('Label'))
    project  = models.ForeignKey(Project,
                                 verbose_name=_('Project'))
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_('Balance'),
    )
    balance_initial = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_('Initial balance'),
        help_text=_('Initial balance will automatically update the balance.'),
    )
    currency = models.CharField(
        max_length=3,
        choices=get_currencies(),
        verbose_name=_('Currency'),
    )
    owners = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        #limit_choices_to= {'user':user}, #{'is_staff': False, 'is_superuser': False},
        verbose_name=_('Owners'),
        related_name='bankaccounts',
        #db_table='bankaccounts_owners',
    )

    objects = BankAccountManager()

    class Meta:
        db_table = 'bankaccounts'
        permissions = (("administer_owners", "Administer owners"),)

    def __str__(self):
        return self.label

    def save(self, *args, **kwargs):

        # Init balance. Merge both just in case.
        if self.pk is None:
            self.balance += self.balance_initial
        # Otherwise update it with the new delta.
        else:
            original = BankAccount.objects.get(pk=self.pk)
            self.balance += self.balance_initial - original.balance_initial

        super(BankAccount, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('banktransactions:list', kwargs={
            'bankaccount_pk': self.pk,
        })
