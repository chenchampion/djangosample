from django.conf.urls import url
from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import AuthenticationForm

from oscar.core.application import (
    DashboardApplication as BaseDashboardApplication)
from oscar.core.loading import get_class
from .views import *

class DashboardApplication(BaseDashboardApplication):
    name = 'dashboard'
    permissions_map = {
        'index': (['is_staff'], ['partner.dashboard_access'], ['customer.dashboard_access']),
        'index_with_date_view': (['is_staff'], ['partner.dashboard_access'], ['customer.dashboard_access']),
        'events-index' : (['is_staff'], ['partner.dashboard_access'], ['customer.dashboard_access']),
        'dashboard-add-event' : (['is_staff'], ['partner.dashboard_access'], ['customer.dashboard_access']),
        'event-detail' : (['is_staff'], ['partner.dashboard_access'], ['customer.dashboard_access']),
    }

    index_view = get_class('dashboard.views', 'IndexView')
    index_with_date_view = get_class('dashboard.views', 'IndexViewWithDate')
    dashboard_event_index = get_class('dashboard.views', 'EventsIndexView')
    reports_app = get_class('dashboard.reports.app', 'application')
    orders_app = get_class('dashboard.orders.app', 'application')
    users_app = get_class('dashboard.users.app', 'application')
    catalogue_app = get_class('dashboard.catalogue.app', 'application')
    promotions_app = get_class('dashboard.promotions.app', 'application')
    pages_app = get_class('dashboard.pages.app', 'application')
    partners_app = get_class('dashboard.partners.app', 'application')
    companys_app = get_class('dashboard.companys.app', 'application')
    investors_app = get_class('dashboard.investors.app', 'application')
    offers_app = get_class('dashboard.offers.app', 'application')
    ranges_app = get_class('dashboard.ranges.app', 'application')
    reviews_app = get_class('dashboard.reviews.app', 'application')
    vouchers_app = get_class('dashboard.vouchers.app', 'application')
    comms_app = get_class('dashboard.communications.app', 'application')
    shipping_app = get_class('dashboard.shipping.app', 'application')
    project_app = get_class('dashboard.project.app', 'application' )
    money_app = get_class('dashboard.money.app', 'application')

    def get_urls(self):
        urls = [
            url(r'^$', self.index_view.as_view(), name='index'),
            url(r'^date/([0-3]?\d)/$', self.index_with_date_view.as_view(), name='index_with_date'),
            url(r'^catalogue/', self.catalogue_app.urls),
            url(r'^reports/', self.reports_app.urls),
            url(r'^orders/', self.orders_app.urls),
            url(r'^users/', self.users_app.urls),
            url(r'^content-blocks/', self.promotions_app.urls),
            url(r'^pages/', self.pages_app.urls),
            url(r'^partners/', self.partners_app.urls),
            url(r'^companys/', self.companys_app.urls),
            url(r'^investors/', self.investors_app.urls),
            url(r'^offers/', self.offers_app.urls),
            url(r'^ranges/', self.ranges_app.urls),
            url(r'^reviews/', self.reviews_app.urls),
            url(r'^vouchers/', self.vouchers_app.urls),
            url(r'^comms/', self.comms_app.urls),
            url(r'^shipping/', self.shipping_app.urls),
            url(r'^projects/', self.project_app.urls),
            url(r'^money/', self.money_app.urls),

            url(r'^login/$', auth_views.login, {
                'template_name': 'dashboard/login.html',
                'authentication_form': AuthenticationForm,
            }, name='login'),
            url(r'^logout/$', auth_views.logout, {
                'next_page': '/',
            }, name='logout'),
            url(r'^calendar/index/$',
                self.dashboard_event_index.as_view(),
                name='events-index'
            ),
            url(
                r'^calendar/(\d{4})/(0?[1-9]|1[012])/$',
                dashboard_month_view,
                name='dashboard-monthly-view'
            ),
            url(
                r'^calendar/(?P<year>\d{4})/$',
                dashboard_year_view,
                name='dashboard-yearly-view'
            ),

            url(
                r'^calendar/(\d{4})/(0?[1-9]|1[012])/([0-3]?\d)/$',
                dashboard_day_view,
                name='dashboard-daily-view'
            ),

            url(
                r'^events/$',
                dashboard_event_listing,
                name='dashboard-events'
            ),
            url(
                r'^events/add/$',
                add_event,
                name='dashboard-add-event'
            ),
            url(
                r'^events/(\d+)/$',
                event_view,
                name='event-detail'
            ),
            url(
                r'^events/(\d+)/(\d+)/$',
                occurrence_view,
                name='dashboard-occurrence'
            ),
        ]
        return self.post_process_urls(urls)


application = DashboardApplication()
