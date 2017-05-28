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
Partner = get_model('partner', 'Partner')
Company = get_model('company', 'Company')
Investor = get_model('investor', 'Investor')
(
    PartnerSearchForm, PartnerCreateForm, PartnerAddressForm,
    NewUserForm, UserEmailForm, ExistingUserForm
) = get_classes(
    'dashboard.partners.forms',
    ['PartnerSearchForm', 'PartnerCreateForm', 'PartnerAddressForm',
     'NewUserForm', 'UserEmailForm', 'ExistingUserForm'])

(ProductClassSelectForm, ProductSearchForm) = get_classes('dashboard.catalogue.forms', ('ProductClassSelectForm', 'ProductSearchForm'))
Product = get_model('catalogue', 'Product')
ProductTable, CategoryTable \
    = get_classes('dashboard.catalogue.tables',
                  ('ProductTable', 'CategoryTable'))
EmailAuthenticationForm, EmailUserCreationForm, OrderSearchForm = get_classes(
    'customer.forms', ['EmailAuthenticationForm', 'EmailUserCreationForm',
                       'OrderSearchForm'])
Order = get_model('order', 'Order')

class PartnerListView(generic.ListView):
    model = Partner
    context_object_name = 'partners'
    template_name = 'dashboard/partners/partner_list.html'
    form_class = PartnerSearchForm

    def get_queryset(self):
        qs = self.model._default_manager.all()
        qs = sort_queryset(qs, self.request, ['name'])

        self.description = _("All partners")

        # We track whether the queryset is filtered to determine whether we
        # show the search form 'reset' button.
        self.is_filtered = False
        self.form = self.form_class(self.request.GET)
        if not self.form.is_valid():
            return qs

        data = self.form.cleaned_data

        if data['name']:
            qs = qs.filter(name__icontains=data['name'])
            self.description = _("Partners matching '%s'") % data['name']
            self.is_filtered = True

        return qs

    def get_context_data(self, **kwargs):
        ctx = super(PartnerListView, self).get_context_data(**kwargs)
        ctx['queryset_description'] = self.description
        ctx['form'] = self.form
        ctx['is_filtered'] = self.is_filtered
        if(self.request):
            ctx['current_user'] = self.request.user
            if(not self.request.user.is_staff):
                my_partners = []
                partners = Partner.objects.all()
                for partner in partners:
                    if (self.request.user in partner.users.all()):
                        my_partners.append(partner)
                ctx['partners'] = my_partners
        return ctx


class PartnerCreateView(generic.CreateView):
    model = Partner
    template_name = 'dashboard/partners/partner_form.html'
    form_class = PartnerCreateForm
    success_url = reverse_lazy('dashboard:partner-list')

    def get_context_data(self, **kwargs):
        ctx = super(PartnerCreateView, self).get_context_data(**kwargs)
        ctx['title'] = _('Create new partner')
        return ctx

    def get_success_url(self):
        messages.success(self.request,
                         _("Partner '%s' was created successfully.") %
                         self.object.name)
        return reverse('dashboard:partner-list')

def filter_products(queryset, user):
    """
    Restrict the queryset to products the given user has access to.
    A staff user is allowed to access all Products.
    A non-staff user is only allowed access to a product if they are in at
    least one stock record's partner user list.
    """
    if user.is_staff:
        return queryset

    return queryset.filter(stockrecords__partner__users__pk=user.pk).distinct()

class PartnerManageView(generic.UpdateView, SingleTableView):
    """
    This multi-purpose view renders out a form to edit the partner's details,
    the associated address and a list of all associated users.
    """
    template_name = 'dashboard/partners/partner_manage.html'
    form_class = PartnerAddressForm
    productclass_form_class = ProductClassSelectForm
    searchform_class = ProductSearchForm
    table_class = ProductTable
    context_table_name = 'products'
    success_url = reverse_lazy('dashboard:partner-list')

    def get_object(self, queryset=None):
        self.partner = get_object_or_404(Partner, pk=self.kwargs['pk'])
        address = self.partner.primary_address
        if address is None:
            address = self.partner.addresses.model(partner=self.partner)
        return address

    def get_initial(self):
        return {'name': self.partner.name}

    def get_context_data(self, **kwargs):
        ctx = super(PartnerManageView, self).get_context_data(**kwargs)
        ctx['partner'] = self.partner
        ctx['title'] = self.partner.name
        ctx['users'] = self.partner.users.all()
        ctx['productclass_form'] = self.productclass_form_class()
        ctx['searchform'] = self.searchform_class()
        #ctx['products'] = Product.objects.filter(partner__name=self.partner.name)
        return ctx

    def form_valid(self, form):
        messages.success(
            self.request, _("Partner '%s' was updated successfully.") %
            self.partner.name)
        self.partner.name = form.cleaned_data['name']
        self.partner.save()
        return super(PartnerManageView, self).form_valid(form)

    def get_description(self, form):
        if form.is_valid() and any(form.cleaned_data.values()):
            return _('Product search results')
        return _('Products')

    def get_table(self, **kwargs):
        if 'recently_edited' in self.request.GET:
            kwargs.update(dict(orderable=False))

        table = super(PartnerManageView, self).get_table(**kwargs)
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
        queryset = self.filter_queryset(queryset)
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

class PartnerDeleteView(generic.DeleteView):
    model = Partner
    template_name = 'dashboard/partners/partner_delete.html'

    def get_success_url(self):
        messages.success(self.request,
                         _("Partner '%s' was deleted successfully.") %
                         self.object.name)
        return reverse('dashboard:partner-list')


# =============
# Partner users
# =============


class PartnerUserCreateView(generic.CreateView):
    model = User
    template_name = 'dashboard/partners/partner_user_form.html'
    form_class = EmailUserCreationForm

    def dispatch(self, request, *args, **kwargs):
        self.partner = get_object_or_404(
            Partner, pk=kwargs.get('partner_pk', None))
        return super(PartnerUserCreateView, self).dispatch(
            request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        #ctx = super(PartnerUserCreateView, self).get_context_data(**kwargs)
        ctx = super(PartnerUserCreateView, self).get_context_data(**kwargs)
        ctx['partner'] = self.partner
        ctx['title'] = _('Create user')
        return ctx

    def get_form_kwargs(self):
        kwargs = super(PartnerUserCreateView, self).get_form_kwargs()
        kwargs['partner'] = self.partner
        return kwargs

    def get_success_url(self):
        name = self.object.get_full_name() or self.object.email
        messages.success(self.request,
                         _("User '%s' was created successfully.") % name)
        return reverse('dashboard:partner-list')


class PartnerUserSelectView(generic.ListView):
    template_name = 'dashboard/partners/partner_user_select.html'
    form_class = UserEmailForm
    context_object_name = 'users'

    def dispatch(self, request, *args, **kwargs):
        self.partner = get_object_or_404(
            Partner, pk=kwargs.get('partner_pk', None))
        return super(PartnerUserSelectView, self).dispatch(
            request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        data = None
        if 'email' in request.GET:
            data = request.GET
        self.form = self.form_class(data)
        return super(PartnerUserSelectView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super(PartnerUserSelectView, self).get_context_data(**kwargs)
        ctx['partner'] = self.partner
        ctx['form'] = self.form
        return ctx

    def get_queryset(self):
        if self.form.is_valid():
            email = normalise_email(self.form.cleaned_data['email'])
            return User.objects.filter(email__icontains=email)
        else:
            return User.objects.none()


class PartnerUserLinkView(generic.View):

    def get(self, request, user_pk, partner_pk):
        # need to allow GET to make Undo link in PartnerUserUnlinkView work
        return self.post(request, user_pk, partner_pk)

    def post(self, request, user_pk, partner_pk):
        user = get_object_or_404(User, pk=user_pk)
        name = user.get_full_name() or user.email
        partner = get_object_or_404(Partner, pk=partner_pk)
        if self.link_user(user, partner):
            messages.success(
                request,
                _("User '%(name)s' was linked to '%(partner_name)s'")
                % {'name': name, 'partner_name': partner.name})
        else:
            messages.info(
                request,
                _("User '%(name)s' is already linked to '%(partner_name)s'")
                % {'name': name, 'partner_name': partner.name})
        return redirect('dashboard:partner-manage', pk=partner_pk)

    def link_user(self, user, partner):
        """
        Links a user to a partner, and adds the dashboard permission if needed.

        Returns False if the user was linked already; True otherwise.
        """
        if partner.users.filter(pk=user.pk).exists():
            return False
        partner.users.add(user)
        if not user.is_staff:
            dashboard_access_perm = Permission.objects.get(
                codename='dashboard_access',
                content_type__app_label='partner')
            user.user_permissions.add(dashboard_access_perm)
        return True


class PartnerUserUnlinkView(generic.View):

    def unlink_user(self, user, partner):
        """
        Unlinks a user from a partner, and removes the dashboard permission
        if they are not linked to any other partners.

        Returns False if the user was not linked to the partner; True
        otherwise.
        """
        if not partner.users.filter(pk=user.pk).exists():
            return False
        partner.users.remove(user)
        if not user.is_staff and not user.partners.exists():
            dashboard_access_perm = Permission.objects.get(
                codename='dashboard_access',
                content_type__app_label='partner')
            user.user_permissions.remove(dashboard_access_perm)
        return True

    def post(self, request, user_pk, partner_pk):
        user = get_object_or_404(User, pk=user_pk)
        name = user.get_full_name() or user.email
        partner = get_object_or_404(Partner, pk=partner_pk)
        if self.unlink_user(user, partner):
            msg = render_to_string(
                'dashboard/partners/messages/user_unlinked.html',
                {'user_name': name,
                 'partner_name': partner.name,
                 'user_pk': user_pk,
                 'partner_pk': partner_pk})
            messages.success(self.request, msg, extra_tags='safe noicon')
        else:
            messages.error(
                request,
                _("User '%(name)s' is not linked to '%(partner_name)s'") %
                {'name': name, 'partner_name': partner.name})
        return redirect('dashboard:partner-manage', pk=partner_pk)


# =====
# Users
# =====


class PartnerUserUpdateView(generic.UpdateView):
    template_name = 'dashboard/partners/partner_user_form.html'
    form_class = ExistingUserForm

    def get_object(self, queryset=None):
        self.partner = get_object_or_404(Partner, pk=self.kwargs['partner_pk'])
        return get_object_or_404(User,
                                 pk=self.kwargs['user_pk'],
                                 partners__pk=self.kwargs['partner_pk'])

    def get_context_data(self, **kwargs):
        ctx = super(PartnerUserUpdateView, self).get_context_data(**kwargs)
        name = self.object.get_full_name() or self.object.email
        ctx['partner'] = self.partner
        ctx['title'] = _("Edit user '%s'") % name
        return ctx

    def get_success_url(self):
        name = self.object.get_full_name() or self.object.email
        messages.success(self.request,
                         _("User '%s' was updated successfully.") % name)
        return reverse('dashboard:partner-list')

class PartnerMembersView(generic.ListView):
    """
    This multi-purpose view renders out a form to edit the company's details,
    the associated address and a list of all associated users.
    """
    template_name = 'dashboard/partners/partner_members.html'
    model = Partner
    success_url = reverse_lazy('dashboard:partner-list')

    def get_queryset(self):
        return None

    def get_context_data(self, **kwargs):
        ctx = super(PartnerMembersView, self).get_context_data(**kwargs)
        if(self.request):
            ctx['current_user'] = self.request.user
            my_partners = []
            partners = Partner.objects.all()
            for partner in partners:
                if (self.request.user in partner.users.all()):
                    my_partners.append(partner)
            ctx['partner'] = my_partners[0]
            ctx['users'] = my_partners[0].users.all()
        return ctx

class PartnerOrderView(generic.ListView):
    """
    This multi-purpose view renders out a form to edit the company's details,
    the associated address and a list of all associated users.
    """
    searchform_class = OrderSearchForm
    template_name = 'dashboard/partners/partner_orders.html'

    def get_queryset(self):
        return None

    def get_context_data(self, **kwargs):
        ctx = super(PartnerOrderView, self).get_context_data(**kwargs)
        if(self.request):
            ctx['current_user'] = self.request.user
            my_companys = []
            orders = []
            companys = Partner.objects.all()
            for company in companys:
                if (self.request.user in company.users.all()):
                    my_companys.append(company)
            for company in my_companys:
                for user in company.users.all():
                    orders += (Order.objects.filter(user=user))
            ctx['orders'] = orders
            ctx['searchform'] = self.searchform_class()
        return ctx

class PartnerCustomerOrderView(generic.ListView):
    """
    This multi-purpose view renders out a form to edit the company's details,
    the associated address and a list of all associated users.
    """
    template_name = 'dashboard/partners/partner_customer_orders.html'
    searchform_class = OrderSearchForm

    def get_queryset(self):
        return None

    def get_context_data(self, **kwargs):
        ctx = super(PartnerCustomerOrderView, self).get_context_data(**kwargs)
        if(self.request):
            ctx['current_user'] = self.request.user
            my_partners = []
            partner = None
            partners = Partner.objects.all()
            orders = []
            for partner in partners:
                if (ctx['current_user'] in partner.users.all()):
                    my_partners.append(partner)
            for partner in my_partners:
                order_lines = partner.order_lines.all()
                for order_line in order_lines:
                    orders.append(order_line.order)
            ctx['orders'] = orders

            companys = Company.objects.all()
            investors = Investor.objects.all()
            customer_orders = []
            for order in orders:
                customer = None
                for company in companys:
                    if (order.user in company.users.all()):
                        customer = company
                        break
                for investor in investors:
                    if (order.user in investor.users.all()):
                        customer = investor
                        break
                test = {'customer':customer, 'order':order}
                tasks = order.task_set.all()
                linked_task = None
                for task in tasks:
                    if task.user_responsible in partner.users.all():
                        linked_task = task
                        break
                customer_orders.append((customer, order, linked_task))


            ctx['customer_orders'] = customer_orders
            ctx['searchform'] = self.searchform_class()
        return ctx