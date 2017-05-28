from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class CompanysDashboardConfig(AppConfig):
    label = 'companys_dashboard'
    name = 'oscar.apps.dashboard.companys'
    verbose_name = _('Companys dashboard')
