from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class MoneyDashboardConfig(AppConfig):
    label = 'money_dashboard'
    name = 'oscar.apps.dashboard.money'
    verbose_name = 'Money'#_('Money dashboard')
