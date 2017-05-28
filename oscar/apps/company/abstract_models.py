from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import pgettext_lazy

from oscar.apps.company.exceptions import InvalidStockAdjustment
from oscar.core.compat import AUTH_USER_MODEL
from oscar.core.utils import get_default_currency
from oscar.models.fields import AutoSlugField
from django.utils.translation import get_language, pgettext_lazy
from django.core.cache import cache
from django.core.urlresolvers import reverse


@python_2_unicode_compatible
class AbstractCompany(models.Model):
    """
    A fulfillment company. An individual or company who can fulfil products.
    E.g. for physical goods, somebody with a warehouse and means of delivery.

    Creating one or more instances of the Company model is a required step in
    setting up an Oscar deployment. Many Oscar deployments will only have one
    fulfillment company.
    """
    code = AutoSlugField(_("Code"), max_length=128, unique=True,
                         populate_from='name')
    name = models.CharField(
        pgettext_lazy(u"Company's name", u"Name"), max_length=128, blank=True)

    #: A company can have users assigned to it. This is used
    #: for access modelling in the permission-based dashboard
    users = models.ManyToManyField(
        AUTH_USER_MODEL, related_name="companys",
        blank=True, verbose_name=_("Users"))

    @property
    def display_name(self):
        return self.name or self.code

    @property
    def primary_address(self):
        """
        Returns a companys primary address. Usually that will be the
        headquarters or similar.

        This is a rudimentary implementation that raises an error if there's
        more than one address. If you actually want to support multiple
        addresses, you will likely need to extend CompanyAddress to have some
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
                "supports one CompanyAddress.  You need to override the "
                "primary_address to look up the right address")


    class Meta:
        abstract = True
        app_label = 'company'
        ordering = ('name', 'code')
        permissions = (('dashboard_access', 'Can access dashboard'), )
        verbose_name = _('Fulfillment company')
        verbose_name_plural = _('Fulfillment companys')

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
                'company:detail',
                kwargs={'product_slug': self.code, 'pk': self.pk})
            cache.set(cache_key, url)
        return url

class AbstractCompanyProspectus(models.Model):
    """
    A company can have one or more addresses. This can be useful e.g. when
    determining US tax which depends on the origin of the shipment.
    """
    UNCONFIRMED, ACTIVE, CANCELLED, CLOSED = (
        'Unconfirmed', 'Active', 'Cancelled', 'Closed')
    STATUS_CHOICES = (
        (UNCONFIRMED, _('Not yet confirmed')),
        (ACTIVE, _('Active')),
        (CANCELLED, _('Cancelled')),
        (CLOSED, _('Closed')),
    )
    title = models.CharField(
        pgettext_lazy(u"Company prospectus's title", u"Title"), max_length=128, blank=True)

    company = models.ForeignKey(
        'company.Company',
        on_delete=models.CASCADE,
        related_name='prospectus',
        verbose_name=_('Company'))

    fundraising_sclae = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Fund raising sclae'),
    )

    total_share_capital = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Total share capital'),
    )

    proposal_details = models.TextField(_('Proposal details'), blank=True)

    image = models.ImageField(_('Image'), upload_to='companys', blank=True,
                              null=True, max_length=255)

    status = models.CharField(_("Status"), max_length=20,
                              choices=STATUS_CHOICES, default=ACTIVE)

    date_created = models.DateTimeField(_("Date Created"), auto_now_add=True)

    class Meta:
        abstract = True
        app_label = 'company'
        verbose_name = _("Company prospectus")
        verbose_name_plural = _("Company prospectus")
