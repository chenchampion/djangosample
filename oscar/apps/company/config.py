from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class CompanyConfig(AppConfig):
    label = 'company'
    name = 'oscar.apps.company'
    verbose_name = _('Company')

