from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class InvestorsDashboardConfig(AppConfig):
    label = 'investors_dashboard'
    name = 'oscar.apps.dashboard.investors'
    verbose_name = _('Investors dashboard')
