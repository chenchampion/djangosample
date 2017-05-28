from django.conf.urls import url

from oscar.core.application import DashboardApplication
from oscar.core.loading import get_class


class InvestorsDashboardApplication(DashboardApplication):
    name = None
    default_permissions = ['is_staff', ]

    permissions_map = {
        'investor-list' : (['is_staff'], ['investor.dashboard_access']),
        'investor-manage': (['is_staff'], ['investor.dashboard_access']),
        'investment-create': (['is_staff'], ['investor.dashboard_access']),
        'investmentcomments-create': (['is_staff'], ['investor.dashboard_access'], ['company.dashboard_access']),
        'investor-member': (['is_staff'], ['investor.dashboard_access']),
        'investor-order': (['is_staff'], ['investor.dashboard_access']),
        'project-announcement-list': (['is_staff'], ['investor.dashboard_access']),
        'project-announcement-create': (['is_staff'], ['investor.dashboard_access']),
        'project-announcement-detail': (['is_staff'], ['investor.dashboard_access']),
        #'create_investment_comments_view': (['is_staff'], ['investor.dashboard_access']),
        #'money-list': (['is_staff'], ['investor.dashboard_access']),
    }

    list_view = get_class('dashboard.investors.views', 'InvestorListView')
    create_view = get_class('dashboard.investors.views', 'InvestorCreateView')
    manage_view = get_class('dashboard.investors.views', 'InvestorManageView')
    delete_view = get_class('dashboard.investors.views', 'InvestorDeleteView')

    create_investment_view = get_class('dashboard.investors.views', 'InvestmentCreateView')

    create_investment_comments_view = get_class('dashboard.investors.views', 'InvestmentCommentsCreateView')


    user_link_view = get_class('dashboard.investors.views',
                               'InvestorUserLinkView')
    user_unlink_view = get_class('dashboard.investors.views',
                                 'InvestorUserUnlinkView')
    user_create_view = get_class('dashboard.investors.views',
                                 'InvestorUserCreateView')
    user_select_view = get_class('dashboard.investors.views',
                                 'InvestorUserSelectView')
    user_update_view = get_class('dashboard.investors.views',
                                 'InvestorUserUpdateView')
    investor_member_view = get_class('dashboard.investors.views', 'InvestorMembersView')
    investor_order_view = get_class('dashboard.investors.views', 'InvestorOrderView')

    project_announcement_create_view = get_class('dashboard.investors.views', 'ProjectAnnouncementCreateView')
    project_announcement_list_view = get_class('dashboard.investors.views', 'ProjectAnnouncementListView')
    project_announcement_detail_view = get_class('dashboard.investors.views', 'ProjectAnnouncementDetailView')
    def get_urls(self):
        urls = [
            url(r'^$', self.list_view.as_view(), name='investor-list'),
            url(r'^create/$', self.create_view.as_view(),
                name='investor-create'),
            url(r'^(?P<pk>\d+)/$', self.manage_view.as_view(),
                name='investor-manage'),
            url(r'^(?P<pk>\d+)/delete/$', self.delete_view.as_view(),
                name='investor-delete'),

            url(r'^(?P<investor_pk>\d+)/users/add/$',
                self.user_create_view.as_view(),
                name='investor-user-create'),
            url(r'^(?P<investor_pk>\d+)/users/select/$',
                self.user_select_view.as_view(),
                name='investor-user-select'),
            url(r'^(?P<investor_pk>\d+)/users/(?P<user_pk>\d+)/link/$',
                self.user_link_view.as_view(), name='investor-user-link'),
            url(r'^(?P<investor_pk>\d+)/users/(?P<user_pk>\d+)/unlink/$',
                self.user_unlink_view.as_view(), name='investor-user-unlink'),
            url(r'^(?P<investor_pk>\d+)/users/(?P<user_pk>\d+)/update/$',
                self.user_update_view.as_view(),
                name='investor-user-update'),

            url(r'^createinvestment/(?P<company_pk>\d+)/(?P<pk>\d+)/$', self.create_investment_view.as_view(),
                name='investment-create'),
            url(r'^createinvestmentcomments/(?P<company_pk>\d+)/(?P<prospectus_pk>\d+)/(?P<pk>\d+)/$', self.create_investment_comments_view.as_view(),
                name='investmentcomments-create'),
            url(r'^investor/members/$', self.investor_member_view.as_view(), name='investor-member'),
            url(r'^investor/orders/$', self.investor_order_view.as_view(), name='investor-order'),
            url(r'^projectannouncementlist/$', self.project_announcement_list_view.as_view(),
                name='project-announcement-list'),
            url(r'^createprojectannouncement/(?P<investor_pk>\d+)/$', self.project_announcement_create_view.as_view(),
                name='project-announcement-create'),
            url(r'^detailprojectannouncement/(?P<investor_pk>\d+)/(?P<pk>\d+)/$',
                self.project_announcement_detail_view.as_view(),
                name='project-announcement-detail'),
        ]
        return self.post_process_urls(urls)


application = InvestorsDashboardApplication()
