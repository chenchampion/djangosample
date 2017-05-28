from django.core.urlresolvers import reverse
from django.views.generic import RedirectView, TemplateView
from oscar.core.loading import get_classes, get_model
from oscar.core.compat import get_user_model

User = get_user_model()
Partner = get_model('partner', 'Partner')

class HomeView(TemplateView):
    """
    This is the home page and will typically live at /
    """
    template_name = 'promotions/home.html'

    def get_context_data(self, *args, **kwargs):
        if(self.request and self.request.user and (not self.request.user.is_anonymous)):
            partners = Partner.objects.filter(users__in=[self.request.user])
        else:
            return {}

        return {'partners': partners}

class RecordClickView(RedirectView):
    """
    Simple RedirectView that helps recording clicks made on promotions
    """
    permanent = False
    model = None

    def get_redirect_url(self, **kwargs):
        try:
            prom = self.model.objects.get(pk=kwargs['pk'])
        except self.model.DoesNotExist:
            return reverse('promotions:home')

        if prom.promotion.has_link:
            prom.record_click()
            return prom.link_url
        return reverse('promotions:home')
