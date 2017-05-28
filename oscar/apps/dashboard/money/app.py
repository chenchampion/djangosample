from django.conf.urls import url

from oscar.core.application import DashboardApplication
from oscar.core.loading import get_class
from mymoney.apps.bankaccounts.views import *

class MoneyDashboardApplication(DashboardApplication):
    name = None
    default_permissions = ['is_staff', ]

    permissions_map = {
        'mymoney-list': (['is_staff'], ['company.dashboard_access'], ['partner.dashboard_access'], ['investor.dashboard_access']),
        'mymoney-create': (['is_staff'], ['company.dashboard_access'], ['partner.dashboard_access']),
        'mymoney-delete': (['is_staff'], ['company.dashboard_access'], ['partner.dashboard_access']),
        'mymoney-update': (['is_staff'], ['company.dashboard_access'], ['partner.dashboard_access']),
        'mymoney-expenselist': (['is_staff'], ['company.dashboard_access'], ['partner.dashboard_access']),
        'mymoney-expense-create': (['is_staff'], ['company.dashboard_access'], ['partner.dashboard_access']),
    }

    list_view = get_class('dashboard.money.views', 'BankAccountListView')
    create_view = get_class('dashboard.money.views', 'NewBankAccountCreateView')
    delete_view = get_class('dashboard.money.views', 'BankAccountDeleteView')
    update_view = get_class('dashboard.money.views', 'BankAccountUpdateView')
    expenseslist_view = get_class('dashboard.money.views', 'ExpenseListView')
    create_expense_view = get_class('dashboard.money.views', 'ExpenseCreateView')

    def get_urls(self):
        urls = [
            url(r'^$', self.list_view.as_view(), name='mymoney-list'),
            #url(r'^$', self.order_list_view.as_view(),name='mymoney-list'),
            url(r'^create/$', self.create_view.as_view(),
                name='mymoney-create'),
            url(
                r'^(?P<pk>\d+)/delete/$',
                self.delete_view.as_view(),
                name='mymoney-delete'
            ),
            url(
                r'^(?P<pk>\d+)/update/$',
                self.update_view.as_view(),
                name='mymoney-update'
            ),
            url(
                r'^(?P<pk>\w+)/expenseslist/$',
                self.expenseslist_view.as_view(),
                name='mymoney-expenselist'
            ),
            url(r'^(?P<name>\w+)/expense/(?P<pk>\d+)/create/$', self.create_expense_view.as_view(),
                name='mymoney-expense-create'),
        ]
        return self.post_process_urls(urls)


application = MoneyDashboardApplication()
