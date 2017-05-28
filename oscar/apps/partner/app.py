from django.conf.urls import url

from oscar.core.application import Application
from oscar.core.loading import get_class


class BasePartnerApplication(Application):
    name = 'partner'
    detail_view = get_class('partner.views', 'PartnerDetailView')
    catalogue_view = get_class('partner.views', 'CatalogueView')
    category_view = get_class('partner.views', 'PartnerCategoryView')


    def get_urls(self):
        urlpatterns = super(BasePartnerApplication, self).get_urls()
        urlpatterns += [
            url(r'^$', self.catalogue_view.as_view(), name='index'),
            url(r'^(?P<product_slug>[\w-]*)_(?P<pk>\d+)/$',
                self.detail_view.as_view(), name='detail'),
            url(r'^category/(?P<category_slug>[\w-]+(/[\w-]+)*)_(?P<pk>\d+)/$',
                self.category_view.as_view(), name='category'),
            # Fallback URL if a user chops of the last part of the URL
            url(r'^category/(?P<category_slug>[\w-]+(/[\w-]+)*)/$',
                self.category_view.as_view())]
        return self.post_process_urls(urlpatterns)


application = BasePartnerApplication()
