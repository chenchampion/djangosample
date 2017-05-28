from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth.views import login, logout_then_login
from django.views.i18n import JavaScriptCatalog

from mymoney.mymoneycore.forms import MyMoneyAuthenticationForm
from mymoney.mymoneycore.views import HomePageRedirectView

urlpatterns = [
    url(r'^{0}/'.format(settings.MYMONEY['ADMIN_BASE_URL']), admin.site.urls),
    url(r'^jsi18n/$', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    url(r'^bank-account/', include(
        'mymoney.apps.bankaccounts.urls', namespace='bankaccounts'
    )),
    url(r'^bank-transaction/', include(
        'mymoney.apps.banktransactions.urls', namespace='banktransactions'
    )),
    url(r'^bank-transaction-tag/', include(
        'mymoney.apps.banktransactiontags.urls',
        namespace='banktransactiontags'
    )),
    url(r'^bank-transaction-scheduler/', include(
        'mymoney.apps.banktransactionschedulers.urls',
        namespace='banktransactionschedulers'
    )),
    url(r'^bank-transaction-analytic/', include(
        'mymoney.apps.banktransactionanalytics.urls',
        namespace='banktransactionanalytics'
    )),
    url(r'^login/$', login, name='login', kwargs={
        'authentication_form': MyMoneyAuthenticationForm
    }),
    url(r'^logout/$', logout_then_login, name='logout'),
    url(r'^$', HomePageRedirectView.as_view(), name='money-home'),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [ url(r'^__debug__/', include(debug_toolbar.urls)), ]
admin.site.site_header = 'MyMoney'
