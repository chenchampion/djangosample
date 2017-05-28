# -*- coding: utf-8 -*-
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import pgettext_lazy

from oscar.apps.investor.exceptions import InvalidStockAdjustment
from oscar.core.compat import AUTH_USER_MODEL
from oscar.core.utils import get_default_currency
from oscar.models.fields import AutoSlugField
from django.utils.translation import get_language, pgettext_lazy
from django.core.cache import cache
from django.core.urlresolvers import reverse


@python_2_unicode_compatible
class AbstractInvestor(models.Model):
    """
    A fulfillment partner. An individual or company who can fulfil products.
    E.g. for physical goods, somebody with a warehouse and means of delivery.

    Creating one or more instances of the Partner model is a required step in
    setting up an Oscar deployment. Many Oscar deployments will only have one
    fulfillment partner.
    """
    code = AutoSlugField(_("Code"), max_length=128, unique=True,
                         populate_from='name')
    name = models.CharField(
        pgettext_lazy(u"Investor's name", u"Name"), max_length=128, blank=True)

    #: A partner can have users assigned to it. This is used
    #: for access modelling in the permission-based dashboard
    users = models.ManyToManyField(
        AUTH_USER_MODEL, related_name="investors",
        blank=True, verbose_name=_("Users"))

    @property
    def display_name(self):
        return self.name or self.code

    @property
    def primary_address(self):
        """
        Returns a partners primary address. Usually that will be the
        headquarters or similar.

        This is a rudimentary implementation that raises an error if there's
        more than one address. If you actually want to support multiple
        addresses, you will likely need to extend PartnerAddress to have some
        field or flag to base your decision on.
        """
        addresses = self.addresses.all()
        if len(addresses) == 0:  # intentionally using len() to save queries
            return None
        elif len(addresses) == 1:
            return addresses[0]
        else:
            raise NotImplementedError(
                "Oscar's default implementation of primary_address only "
                "supports one InvestorAddress.  You need to override the "
                "primary_address to look up the right address")

    class Meta:
        abstract = True
        app_label = 'investor'
        ordering = ('name', 'code')
        permissions = (('dashboard_access', 'Can access dashboard'), )
        verbose_name = _('Fulfillment investor')
        verbose_name_plural = _('Fulfillment investors')

    def __str__(self):
        return self.display_name


    def get_absolute_url(self):
        """
        Our URL scheme means we have to look up the category's ancestors. As
        that is a bit more expensive, we cache the generated URL. That is
        safe even for a stale cache, as the default implementation of
        ProductCategoryView does the lookup via primary key anyway. But if
        you change that logic, you'll have to reconsider the caching
        approach.
        """
        current_locale = get_language()
        cache_key = 'CATEGORY_URL_%s_%s' % (current_locale, self.pk)
        url = cache.get(cache_key)
        url = None
        if not url:
            url = reverse(
                'investor:detail',
                kwargs={'product_slug': self.code, 'pk': self.pk})
            cache.set(cache_key, url)
        return url

class AbstractInvestment(models.Model):
    SUBMITTED, CONFIRMED, REJECTED = (
        'Submitted', 'Confirmed', 'Rejected')
    STATUS_CHOICES = (
        (SUBMITTED, _('Submitted')),
        (CONFIRMED, _('Confirmed')),
        (REJECTED, _('Rejected')),
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Amount'),
    )
    prospectus = models.ForeignKey(
        'company.CompanyProspectus',
        on_delete=models.CASCADE, null=True, blank=True)


    user = models.ForeignKey(
        AUTH_USER_MODEL,
        blank=True, null=True, verbose_name=_("User"))

    investor = models.ForeignKey(
        'investor.Investor',
        blank=True, null=True, verbose_name=_("Investor"))

    status = models.CharField(_("Status"), max_length=20,
                              choices=STATUS_CHOICES, default=SUBMITTED)

    date_created = models.DateTimeField(_("Date Created"), auto_now_add=True)


class AbstractInvestmentComment(models.Model):
    comment = models.CharField( max_length=128, blank=True, default='')

    investment = models.ForeignKey(
        'investor.Investment',
        on_delete=models.CASCADE,
        blank=True, null=True,
        related_name='Investment',
        verbose_name=_('Investment'))

    date_created = models.DateTimeField(_("Date Created"), auto_now_add=True)

    user = models.ForeignKey(
        AUTH_USER_MODEL,
        blank=True, null=True, verbose_name=_("User"))


class AbstractProjectAnnouncement(models.Model):
    """
    A company can have one or more addresses. This can be useful e.g. when
    determining US tax which depends on the origin of the shipment.
    """
    ACTIVE, CANCELLED, CLOSED = (
        'Active', 'Cancelled', 'Closed')
    STATUS_CHOICES = (
        (ACTIVE, _('Active')),
        (CANCELLED, _('Cancelled')),
        (CLOSED, _('Closed')),
    )

    JOINT, PROJECT = (
        '创建合资公司', '项目招标')
    PROPOSAL_CHOICES = (
        (JOINT, _('Joint Venture')),
        (PROJECT, _('Project tender')),
    )

    A_QUARTER, HALF, THREE_QUARTERS, ALL = (
        '25%', '50%', '75%', '100%')
    SHARE_RATIO_CHOICES = (
        (A_QUARTER, _('25%')),
        (HALF, _('50%')),
        (THREE_QUARTERS, _('75%')),
        (ALL, _('100%')),
    )

    title = models.CharField(
        pgettext_lazy(u"Investor project announcement's title", u"Title"), max_length=128, blank=True)

    investor = models.ForeignKey(
        'investor.Investor',
        on_delete=models.CASCADE,
        related_name='projectannouncement',
        verbose_name=_('Investor'))

    proposal = models.CharField(_("Proposal"), max_length=20,
                              choices=PROPOSAL_CHOICES, default=JOINT)

    scale_of_funding = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Scale of funding'),
    )

    share_ratio = models.CharField(_("Share ratio"), max_length=20,
                              choices=SHARE_RATIO_CHOICES, default=ALL)


    proposal_details = models.TextField(_('Proposal details'), blank=True)


    status = models.CharField(_("Status"), max_length=20,
                              choices=STATUS_CHOICES, default=ACTIVE)

    date_created = models.DateTimeField(_("Date Created"), auto_now_add=True)

    class Meta:
        abstract = True
        app_label = 'investor'
        verbose_name = _("Investor Project Announcement")
        verbose_name_plural = _("Investor Project Announcement")