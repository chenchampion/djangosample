from django.conf.urls import url

from oscar.core.application import DashboardApplication
from oscar.core.loading import get_class


class CompanysDashboardApplication(DashboardApplication):
    name = None
    default_permissions = ['is_staff', ]

    permissions_map = {
        'company-list' : (['is_staff'], ['company.dashboard_access']),
        'company-manage': (['is_staff'], ['company.dashboard_access']),
        'company-prospectus-create': (['is_staff'], ['company.dashboard_access']),
        'company-prospectus-delete': (['is_staff'], ['company.dashboard_access']),
        'company-prospectus-detail': (['is_staff'], ['company.dashboard_access'], ['investor.dashboard_access']),
        'company-prospectus-update': (['is_staff'], ['company.dashboard_access']),
        'company-prospectus-list': (['is_staff'], ['company.dashboard_access']),
        'company-order': (['is_staff'], ['company.dashboard_access']),
        'company-member': (['is_staff'], ['company.dashboard_access']),
        'money-list': (['is_staff'], ['company.dashboard_access']),
    }

    list_view = get_class('dashboard.companys.views', 'CompanyListView')
    create_view = get_class('dashboard.companys.views', 'CompanyCreateView')
    manage_view = get_class('dashboard.companys.views', 'CompanyManageView')
    delete_view = get_class('dashboard.companys.views', 'CompanyDeleteView')
    test_view = get_class('dashboard.money.views', 'CompanyListView')

    company_prospectus_create_view = get_class('dashboard.companys.views', 'CompanyProspectusCreateView')
    company_prospectus_delete_view = get_class('dashboard.companys.views', 'CompanyProspectusDeleteView')
    company_prospectus_update_view = get_class('dashboard.companys.views', 'CompanyProspectusUpdateView')
    company_prospectus_detail_view = get_class('dashboard.companys.views', 'CompanyProspectusDetailView')
    company_prospectus_list_view = get_class('dashboard.companys.views', 'CompanyProspectusView')

    company_order_view = get_class('dashboard.companys.views', 'CompanyOrderView')
    company_member_view = get_class('dashboard.companys.views', 'CompanyMembersView')

    user_link_view = get_class('dashboard.companys.views',
                               'CompanyUserLinkView')
    user_unlink_view = get_class('dashboard.companys.views',
                                 'CompanyUserUnlinkView')
    user_create_view = get_class('dashboard.companys.views',
                                 'CompanyUserCreateView')
    user_select_view = get_class('dashboard.companys.views',
                                 'CompanyUserSelectView')
    user_update_view = get_class('dashboard.companys.views',
                                 'CompanyUserUpdateView')

    def get_urls(self):
        urls = [
            url(r'^$', self.list_view.as_view(), name='company-list'),
            url(r'^create/$', self.create_view.as_view(),
                name='company-create'),
            url(r'^(?P<pk>\d+)/$', self.manage_view.as_view(),
                name='company-manage'),
            url(r'^(?P<pk>\d+)/delete/$', self.delete_view.as_view(),
                name='company-delete'),

            url(r'^(?P<company_pk>\d+)/users/add/$',
                self.user_create_view.as_view(),
                name='company-user-create'),
            url(r'^(?P<company_pk>\d+)/users/select/$',
                self.user_select_view.as_view(),
                name='company-user-select'),
            url(r'^(?P<company_pk>\d+)/users/(?P<user_pk>\d+)/link/$',
                self.user_link_view.as_view(), name='company-user-link'),
            url(r'^(?P<company_pk>\d+)/users/(?P<user_pk>\d+)/unlink/$',
                self.user_unlink_view.as_view(), name='company-user-unlink'),
            url(r'^(?P<company_pk>\d+)/users/(?P<user_pk>\d+)/update/$',
                self.user_update_view.as_view(),
                name='company-user-update'),
            url(r'^test/$', self.test_view.as_view(), name='test-list'),
            url(r'^createprospectus/(?P<company_pk>\d+)/$', self.company_prospectus_create_view.as_view(),
                name='company-prospectus-create'),
            url(r'^deleteprospectus/(?P<company_pk>\d+)/(?P<pk>\d+)/$', self.company_prospectus_delete_view.as_view(),
                name='company-prospectus-delete'),
            url(r'^updateprospectus/(?P<company_pk>\d+)/(?P<pk>\d+)/$',
                self.company_prospectus_update_view.as_view(),
                name='company-prospectus-update'),
            url(r'^detailprospectus/(?P<company_pk>\d+)/(?P<pk>\d+)/$',
                self.company_prospectus_detail_view.as_view(),
                name='company-prospectus-detail'),
            url(r'^listprospectus/(?P<pk>\d+)/$',
                self.company_prospectus_list_view.as_view(),
                name='company-prospectus-list'),
            url(r'^company/orders/$', self.company_order_view.as_view(), name='company-order'),
            url(r'^company/members/$', self.company_member_view.as_view(), name='company-member'),
        ]
        return self.post_process_urls(urls)


application = CompanysDashboardApplication()
