from django.contrib import messages
from django.contrib.auth.models import Permission
from django.core.urlresolvers import reverse, reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from django.views import generic

from oscar.apps.customer.utils import normalise_email
from oscar.core.compat import get_user_model
from oscar.core.loading import get_classes, get_model
from oscar.views import sort_queryset
from django_tables2 import SingleTableMixin, SingleTableView

User = get_user_model()
Company = get_model('company', 'Company')
CompanyProspectus = get_model('company', 'CompanyProspectus')
Investment = get_model('investor', 'Investment')
InvestmentComment = get_model('investor', 'InvestmentComment')

(
    CompanySearchForm, CompanyCreateForm, CompanyAddressForm,
    NewUserForm, UserEmailForm, ExistingUserForm, CompanyProspectusCreateForm
) = get_classes(
    'dashboard.companys.forms',
    ['CompanySearchForm', 'CompanyCreateForm', 'CompanyAddressForm',
     'NewUserForm', 'UserEmailForm', 'ExistingUserForm', 'CompanyProspectusCreateForm'])

(ProductClassSelectForm, ProductSearchForm) = get_classes('dashboard.catalogue.forms', ('ProductClassSelectForm', 'ProductSearchForm'))
Product = get_model('catalogue', 'Product')
ProductTable, CategoryTable \
    = get_classes('dashboard.catalogue.tables',
                  ('ProductTable', 'CategoryTable'))
EmailAuthenticationForm, EmailUserCreationForm, OrderSearchForm = get_classes(
    'customer.forms', ['EmailAuthenticationForm', 'EmailUserCreationForm',
                       'OrderSearchForm'])
Order = get_model('order', 'Order')

class CompanyListView(generic.ListView):
    model = Company
    context_object_name = 'companys'
    template_name = 'dashboard/companys/company_list.html'
    form_class = CompanySearchForm

    def get_queryset(self):
        qs = self.model._default_manager.all()
        qs = sort_queryset(qs, self.request, ['name'])

        self.description = _("All companys")

        # We track whether the queryset is filtered to determine whether we
        # show the search form 'reset' button.
        self.is_filtered = False
        self.form = self.form_class(self.request.GET)
        if not self.form.is_valid():
            return qs

        data = self.form.cleaned_data

        if data['name']:
            qs = qs.filter(name__icontains=data['name'])
            self.description = _("Companys matching '%s'") % data['name']
            self.is_filtered = True

        return qs

    def get_context_data(self, **kwargs):
        ctx = super(CompanyListView, self).get_context_data(**kwargs)
        ctx['queryset_description'] = self.description
        ctx['form'] = self.form
        ctx['is_filtered'] = self.is_filtered
        return ctx


class CompanyCreateView(generic.CreateView):
    model = Company
    template_name = 'dashboard/companys/company_form.html'
    form_class = CompanyCreateForm
    success_url = reverse_lazy('dashboard:company-list')

    def get_context_data(self, **kwargs):
        ctx = super(CompanyCreateView, self).get_context_data(**kwargs)
        ctx['title'] = _('Create new company')
        return ctx

    def get_success_url(self):
        messages.success(self.request,
                         _("Company '%s' was created successfully.") %
                         self.object.name)
        return reverse('dashboard:company-list')

def filter_products(queryset, user):
    """
    Restrict the queryset to products the given user has access to.
    A staff user is allowed to access all Products.
    A non-staff user is only allowed access to a product if they are in at
    least one stock record's company user list.
    """
    if user.is_staff:
        return queryset

    return queryset.filter(stockrecords__company__users__pk=user.pk).distinct()

class CompanyManageView(generic.UpdateView, SingleTableView):
    """
    This multi-purpose view renders out a form to edit the company's details,
    the associated address and a list of all associated users.
    """
    template_name = 'dashboard/companys/company_manage.html'
    form_class = CompanyAddressForm
    productclass_form_class = ProductClassSelectForm
    searchform_class = OrderSearchForm
    table_class = ProductTable
    success_url = reverse_lazy('dashboard:company-list')

    def get_object(self, queryset=None):
        self.company = get_object_or_404(Company, pk=self.kwargs['pk'])
        address = self.company.primary_address
        if address is None:
            address = self.company.addresses.model(company=self.company)
        return address

    def get_initial(self):
        return {'name': self.company.name}

    def get_context_data(self, **kwargs):
        ctx = super(CompanyManageView, self).get_context_data(**kwargs)
        ctx['company'] = self.company
        ctx['title'] = self.company.name
        ctx['users'] = self.company.users.all()
        ctx['productclass_form'] = self.productclass_form_class()
        ctx['searchform'] = self.searchform_class()
        ctx['prospectuses'] = CompanyProspectus.objects.filter(company__pk=self.kwargs['pk'])
        if(self.request):
            ctx['current_user'] = self.request.user
            my_companys = []
            orders = []
            companys = Company.objects.all()
            for company in companys:
                if (self.request.user in company.users.all()):
                    my_companys.append(company)
            for company in my_companys:
                for user in company.users.all():
                    orders += (Order.objects.filter(user=user))
            ctx['orders'] = orders
        return ctx

    def form_valid(self, form):
        messages.success(
            self.request, _("Company '%s' was updated successfully.") %
            self.company.name)
        self.company.name = form.cleaned_data['name']
        self.company.save()
        return super(CompanyManageView, self).form_valid(form)

    def get_description(self, form):
        if form.is_valid() and any(form.cleaned_data.values()):
            return _('Product search results')
        return _('Products')

    def get_table(self, **kwargs):
        if 'recently_edited' in self.request.GET:
            kwargs.update(dict(orderable=False))

        table = super(CompanyManageView, self).get_table(**kwargs)
        table.caption = self.get_description(self.form)
        return table

    def get_table_pagination(self, table):
        return dict(per_page=20)

    def filter_queryset(self, queryset):
        """
        Apply any filters to restrict the products that appear on the list
        """
        return filter_products(queryset, self.request.user)

    def get_queryset(self):
        """
        Build the queryset for this list
        """
        queryset = Product.browsable.base_queryset()
        #queryset = self.filter_queryset(queryset)
        queryset = self.apply_search(queryset)
        return queryset

    def apply_search(self, queryset):
        """
        Filter the queryset and set the description according to the search
        parameters given
        """
        self.form = self.form_class(self.request.GET)

        if not self.form.is_valid():
            return queryset

        data = self.form.cleaned_data

        if data.get('upc'):
            # Filter the queryset by upc
            # If there's an exact match, return it, otherwise return results
            # that contain the UPC
            matches_upc = Product.objects.filter(upc=data['upc'])
            qs_match = queryset.filter(
                Q(id__in=matches_upc.values('id')) |
                Q(id__in=matches_upc.values('parent_id')))

            if qs_match.exists():
                queryset = qs_match
            else:
                matches_upc = Product.objects.filter(upc__icontains=data['upc'])
                queryset = queryset.filter(
                    Q(id__in=matches_upc.values('id')) | Q(id__in=matches_upc.values('parent_id')))

        if data.get('title'):
            queryset = queryset.filter(title__icontains=data['title'])

        return queryset

class CompanyDeleteView(generic.DeleteView):
    model = Company
    template_name = 'dashboard/companys/company_delete.html'

    def get_success_url(self):
        messages.success(self.request,
                         _("Company '%s' was deleted successfully.") %
                         self.object.name)
        return reverse('dashboard:company-list')


# =============
# Company users
# =============


class CompanyUserCreateView(generic.CreateView):
    model = User
    template_name = 'dashboard/companys/company_user_form.html'
    form_class = NewUserForm

    def dispatch(self, request, *args, **kwargs):
        self.company = get_object_or_404(
            Company, pk=kwargs.get('company_pk', None))
        return super(CompanyUserCreateView, self).dispatch(
            request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super(CompanyUserCreateView, self).get_context_data(**kwargs)
        ctx['company'] = self.company
        ctx['title'] = _('Create user')
        return ctx

    def get_form_kwargs(self):
        kwargs = super(CompanyUserCreateView, self).get_form_kwargs()
        kwargs['company'] = self.company
        return kwargs

    def get_success_url(self):
        name = self.object.get_full_name() or self.object.email
        messages.success(self.request,
                         _("User '%s' was created successfully.") % name)
        return reverse('dashboard:company-list')


class CompanyUserSelectView(generic.ListView):
    template_name = 'dashboard/companys/company_user_select.html'
    form_class = UserEmailForm
    context_object_name = 'users'

    def dispatch(self, request, *args, **kwargs):
        self.company = get_object_or_404(
            Company, pk=kwargs.get('company_pk', None))
        return super(CompanyUserSelectView, self).dispatch(
            request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        data = None
        if 'email' in request.GET:
            data = request.GET
        self.form = self.form_class(data)
        return super(CompanyUserSelectView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super(CompanyUserSelectView, self).get_context_data(**kwargs)
        ctx['company'] = self.company
        ctx['form'] = self.form
        return ctx

    def get_queryset(self):
        if self.form.is_valid():
            email = normalise_email(self.form.cleaned_data['email'])
            return User.objects.filter(email__icontains=email)
        else:
            return User.objects.none()


class CompanyUserLinkView(generic.View):

    def get(self, request, user_pk, company_pk):
        # need to allow GET to make Undo link in CompanyUserUnlinkView work
        return self.post(request, user_pk, company_pk)

    def post(self, request, user_pk, company_pk):
        user = get_object_or_404(User, pk=user_pk)
        name = user.get_full_name() or user.email
        company = get_object_or_404(Company, pk=company_pk)
        if self.link_user(user, company):
            messages.success(
                request,
                _("User '%(name)s' was linked to '%(company_name)s'")
                % {'name': name, 'company_name': company.name})
        else:
            messages.info(
                request,
                _("User '%(name)s' is already linked to '%(company_name)s'")
                % {'name': name, 'company_name': company.name})
        return redirect('dashboard:company-manage', pk=company_pk)

    def link_user(self, user, company):
        """
        Links a user to a company, and adds the dashboard permission if needed.

        Returns False if the user was linked already; True otherwise.
        """
        if company.users.filter(pk=user.pk).exists():
            return False
        company.users.add(user)
        if not user.is_staff:
            dashboard_access_perm = Permission.objects.get(
                codename='dashboard_access',
                content_type__app_label='company')
            user.user_permissions.add(dashboard_access_perm)
        return True


class CompanyUserUnlinkView(generic.View):

    def unlink_user(self, user, company):
        """
        Unlinks a user from a company, and removes the dashboard permission
        if they are not linked to any other companys.

        Returns False if the user was not linked to the company; True
        otherwise.
        """
        if not company.users.filter(pk=user.pk).exists():
            return False
        company.users.remove(user)
        if not user.is_staff and not user.companys.exists():
            dashboard_access_perm = Permission.objects.get(
                codename='dashboard_access',
                content_type__app_label='company')
            user.user_permissions.remove(dashboard_access_perm)
        return True

    def post(self, request, user_pk, company_pk):
        user = get_object_or_404(User, pk=user_pk)
        name = user.get_full_name() or user.email
        company = get_object_or_404(Company, pk=company_pk)
        if self.unlink_user(user, company):
            msg = render_to_string(
                'dashboard/companys/messages/user_unlinked.html',
                {'user_name': name,
                 'company_name': company.name,
                 'user_pk': user_pk,
                 'company_pk': company_pk})
            messages.success(self.request, msg, extra_tags='safe noicon')
        else:
            messages.error(
                request,
                _("User '%(name)s' is not linked to '%(company_name)s'") %
                {'name': name, 'company_name': company.name})
        return redirect('dashboard:company-manage', pk=company_pk)


# =====
# Users
# =====


class CompanyUserUpdateView(generic.UpdateView):
    template_name = 'dashboard/companys/company_user_form.html'
    form_class = ExistingUserForm

    def get_object(self, queryset=None):
        self.company = get_object_or_404(Company, pk=self.kwargs['company_pk'])
        return get_object_or_404(User,
                                 pk=self.kwargs['user_pk'],
                                 companys__pk=self.kwargs['company_pk'])

    def get_context_data(self, **kwargs):
        ctx = super(CompanyUserUpdateView, self).get_context_data(**kwargs)
        name = self.object.get_full_name() or self.object.email
        ctx['company'] = self.company
        ctx['title'] = _("Edit user '%s'") % name
        return ctx

    def get_success_url(self):
        name = self.object.get_full_name() or self.object.email
        messages.success(self.request,
                         _("User '%s' was updated successfully.") % name)
        return reverse('dashboard:company-list')


class CompanyProspectusCreateView(generic.CreateView):
    model = CompanyProspectus
    template_name = 'dashboard/companys/company_prospectus_form.html'
    form_class = CompanyProspectusCreateForm
    #success_url = reverse_lazy('dashboard:company-manage')

    def get_context_data(self, **kwargs):
        ctx = super(CompanyProspectusCreateView, self).get_context_data(**kwargs)
        ctx['title'] = _('Create new company prospectus')
        ctx['company_pk'] = self.kwargs['company_pk']
        return ctx

    def get_success_url(self):
        messages.success(self.request,
                         _("Company prospectus '%s' was created successfully.") %
                         self.object.title)
        return reverse('dashboard:company-manage',
                       kwargs={'pk': self.kwargs['company_pk']})

class CompanyProspectusDeleteView(generic.DeleteView):
    model = CompanyProspectus
    template_name = 'dashboard/companys/company_prospectus_delete.html'

    def get_context_data(self, **kwargs):
        ctx = super(CompanyProspectusDeleteView, self).get_context_data(**kwargs)
        ctx['company'] = Company.objects.get(pk=self.kwargs['company_pk'])
        return ctx

    def get_success_url(self):
        messages.success(self.request,
                         _("Company prospectus '%s' was deleted successfully.") %
                         self.object.title)
        return reverse('dashboard:company-manage',
                       kwargs={'pk': self.kwargs['company_pk']})

class CompanyProspectusUpdateView(generic.UpdateView):
    model = CompanyProspectus
    template_name = 'dashboard/companys/company_prospectus_form.html'
    form_class = CompanyProspectusCreateForm

    def get_context_data(self, **kwargs):
        ctx = super(CompanyProspectusUpdateView, self).get_context_data(**kwargs)
        ctx['title'] = _('Update prospectus')
        ctx['company_pk'] = self.kwargs['company_pk']
        return ctx

    def get_success_url(self):
        messages.success(self.request,
                         _("Company prospectus '%s' was updated successfully.") %
                         self.object.title)
        return reverse('dashboard:company-manage',
                       kwargs={'pk': self.kwargs['company_pk']})

from django.db.models import Q
class CompanyProspectusDetailView(generic.DetailView):
    model = CompanyProspectus
    template_name = 'dashboard/companys/company_prospectus_detail.html'

    def get_context_data(self, **kwargs):
        ctx = super(CompanyProspectusDetailView, self).get_context_data(**kwargs)
        ctx['title'] = _('Detail of prospectus')
        ctx['company_pk'] = self.kwargs['company_pk']
        ctx['prospectus'] = CompanyProspectus.objects.get(pk=self.kwargs['pk'])
        ctx['investments'] = None
        ctx['is_investor'] = False
        ctx['investment_comments'] = None
        check = self.request.user.has_perm('investor.dashboard_access')
        if check:
            ctx['is_investor'] = True
            investments = Investment.objects.filter(prospectus=ctx['prospectus'])
            ctx['investments'] = investments.filter(user=self.request.user)
            if(len(ctx['investments'])):
                ctx['investment_comments'] = InvestmentComment.objects.filter(investment=ctx['investments'][0])

        check = self.request.user.has_perm('company.dashboard_access')
        if check:
            ctx['comments_list'] = []
            ctx['investments'] = Investment.objects.filter(prospectus=ctx['prospectus'])
            for investment in ctx['investments']:
                comments = InvestmentComment.objects.filter(investment=investment)
                ctx['comments_list'].append((investment, comments))


        return ctx

class CompanyOrderView(generic.ListView):
    """
    This multi-purpose view renders out a form to edit the company's details,
    the associated address and a list of all associated users.
    """
    template_name = 'dashboard/companys/company_orders.html'
    form_class = CompanyAddressForm
    productclass_form_class = ProductClassSelectForm
    searchform_class = OrderSearchForm
    table_class = ProductTable
    model = Company
    success_url = reverse_lazy('dashboard:company-list')

    def get_queryset(self):
        return None

    def get_context_data(self, **kwargs):
        ctx = super(CompanyOrderView, self).get_context_data(**kwargs)
        if(self.request):
            ctx['current_user'] = self.request.user
            my_companys = []
            orders = []
            companys = Company.objects.all()
            for company in companys:
                if (self.request.user in company.users.all()):
                    my_companys.append(company)
            for company in my_companys:
                for user in company.users.all():
                    orders += (Order.objects.filter(user=user))
            ctx['orders'] = orders
            ctx['searchform'] = self.searchform_class()
        return ctx

class CompanyMembersView(generic.ListView):
    """
    This multi-purpose view renders out a form to edit the company's details,
    the associated address and a list of all associated users.
    """
    template_name = 'dashboard/companys/company_members.html'
    form_class = CompanyAddressForm
    productclass_form_class = ProductClassSelectForm
    searchform_class = OrderSearchForm
    table_class = ProductTable
    model = Company
    success_url = reverse_lazy('dashboard:company-list')

    def get_queryset(self):
        return None

    def get_context_data(self, **kwargs):
        ctx = super(CompanyMembersView, self).get_context_data(**kwargs)
        if(self.request):
            ctx['current_user'] = self.request.user
            my_companys = []
            orders = []
            companys = Company.objects.all()
            for company in companys:
                if (self.request.user in company.users.all()):
                    my_companys.append(company)
            ctx['company'] = my_companys[0]
            ctx['users'] = my_companys[0].users.all()
        return ctx

class CompanyProspectusView(generic.ListView):
    """
    This multi-purpose view renders out a form to edit the company's details,
    the associated address and a list of all associated users.
    """
    template_name = 'dashboard/companys/company_prospectuses.html'
    model = CompanyProspectus
    success_url = reverse_lazy('dashboard:company-list')

    def get_queryset(self):
        return None

    def get_context_data(self, **kwargs):
        ctx = super(CompanyProspectusView, self).get_context_data(**kwargs)
        ctx['prospectuses'] = CompanyProspectus.objects.filter(company__pk=self.kwargs['pk'])
        ctx['company'] = Company.objects.get(pk=self.kwargs['pk'])

        return ctx