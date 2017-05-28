from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class InvestorConfig(AppConfig):
    label = 'investor'
    name = 'oscar.apps.investor'
    verbose_name = _('Investor')

    def ready(self):
        from . import receivers  # noqa
