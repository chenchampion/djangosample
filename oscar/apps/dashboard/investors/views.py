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
Investor = get_model('investor', 'Investor')
Investment = get_model('investor', 'Investment')
InvestmentComment = get_model('investor', 'InvestmentComment')
ProjectAnnouncement = get_model('investor', 'ProjectAnnouncement')

(
    InvestorSearchForm, InvestorCreateForm, InvestorAddressForm,
    NewUserForm, UserEmailForm, ExistingUserForm, InvestmentCreateForm, InvestmentCommentsCreateForm, ProjectAnnouncementCreateForm,
    ProjectAnnouncementSearchForm
) = get_classes(
    'dashboard.investors.forms',
    ['InvestorSearchForm', 'InvestorCreateForm', 'InvestorAddressForm',
     'NewUserForm', 'UserEmailForm', 'ExistingUserForm', 'InvestmentCreateForm', 'InvestmentCommentsCreateForm',
     'ProjectAnnouncementCreateForm', 'ProjectAnnouncementSearchForm'])

(ProductClassSelectForm, ProductSearchForm) = get_classes('dashboard.catalogue.forms', ('ProductClassSelectForm', 'ProductSearchForm'))
Product = get_model('catalogue', 'Product')
ProductTable, CategoryTable \
    = get_classes('dashboard.catalogue.tables',
                  ('ProductTable', 'CategoryTable'))
EmailAuthenticationForm, EmailUserCreationForm, OrderSearchForm = get_classes(
    'customer.forms', ['EmailAuthenticationForm', 'EmailUserCreationForm',
                       'OrderSearchForm'])
Order = get_model('order', 'Order')
CompanyProspectus = get_model('company', 'CompanyProspectus')

class InvestorListView(generic.ListView):
    model = Investor
    context_object_name = 'investors'
    template_name = 'dashboard/investors/investor_list.html'
    form_class = InvestorSearchForm

    def get_queryset(self):
        qs = self.model._default_manager.all()
        qs = sort_queryset(qs, self.request, ['name'])

        self.description = _("All investors")

        # We track whether the queryset is filtered to determine whether we
        # show the search form 'reset' button.
        self.is_filtered = False
        self.form = self.form_class(self.request.GET)
        if not self.form.is_valid():
            return qs

        data = self.form.cleaned_data

        if data['name']:
            qs = qs.filter(name__icontains=data['name'])
            self.description = _("Investors matching '%s'") % data['name']
            self.is_filtered = True

        return qs

    def get_context_data(self, **kwargs):
        ctx = super(InvestorListView, self).get_context_data(**kwargs)
        ctx['queryset_description'] = self.description
        ctx['form'] = self.form
        ctx['is_filtered'] = self.is_filtered
        if(self.request):
            ctx['current_user'] = self.request.user
        return ctx


class InvestorCreateView(generic.CreateView):
    model = Investor
    template_name = 'dashboard/investors/investor_form.html'
    form_class = InvestorCreateForm
    success_url = reverse_lazy('dashboard:investor-list')

    def get_context_data(self, **kwargs):
        ctx = super(InvestorCreateView, self).get_context_data(**kwargs)
        ctx['title'] = _('Create new investor')
        return ctx

    def get_success_url(self):
        messages.success(self.request,
                         _("Investor '%s' was created successfully.") %
                         self.object.name)
        return reverse('dashboard:investor-list')

def filter_products(queryset, user):
    """
    Restrict the queryset to products the given user has access to.
    A staff user is allowed to access all Products.
    A non-staff user is only allowed access to a product if they are in at
    least one stock record's investor user list.
    """
    if user.is_staff:
        return queryset

    return queryset.filter(stockrecords__investor__users__pk=user.pk).distinct()

class InvestorManageView(generic.UpdateView, SingleTableView):
    """
    This multi-purpose view renders out a form to edit the investor's details,
    the associated address and a list of all associated users.
    """
    template_name = 'dashboard/investors/investor_manage.html'
    form_class = InvestorAddressForm
    productclass_form_class = ProductClassSelectForm
    searchform_class = OrderSearchForm
    table_class = ProductTable
    success_url = reverse_lazy('dashboard:investor-list')

    def get_object(self, queryset=None):
        self.investor = get_object_or_404(Investor, pk=self.kwargs['pk'])
        address = self.investor.primary_address
        if address is None:
            address = self.investor.addresses.model(investor=self.investor)
        return address

    def get_initial(self):
        return {'name': self.investor.name}

    def get_context_data(self, **kwargs):
        ctx = super(InvestorManageView, self).get_context_data(**kwargs)
        ctx['investor'] = self.investor
        ctx['title'] = self.investor.name
        ctx['users'] = self.investor.users.all()
        ctx['productclass_form'] = self.productclass_form_class()
        ctx['searchform'] = self.searchform_class()
        ctx['prospectuses'] = CompanyProspectus.objects.filter(status='Active')
        if(self.request):
            ctx['current_user'] = self.request.user
            my_investors = []
            orders = []
            investors = Investor.objects.all()
            for investor in investors:
                if (self.request.user in investor.users.all()):
                    my_investors.append(investor)
            for investor in my_investors:
                for user in investor.users.all():
                    orders += (Order.objects.filter(user=user))
            ctx['orders'] = orders
        return ctx

    def form_valid(self, form):
        messages.success(
            self.request, _("Investor '%s' was updated successfully.") %
            self.investor.name)
        self.investor.name = form.cleaned_data['name']
        self.investor.save()
        return super(InvestorManageView, self).form_valid(form)

    def get_description(self, form):
        if form.is_valid() and any(form.cleaned_data.values()):
            return _('Product search results')
        return _('Products')

    def get_table(self, **kwargs):
        if 'recently_edited' in self.request.GET:
            kwargs.update(dict(orderable=False))

        table = super(InvestorManageView, self).get_table(**kwargs)
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

class InvestorDeleteView(generic.DeleteView):
    model = Investor
    template_name = 'dashboard/investors/investor_delete.html'

    def get_success_url(self):
        messages.success(self.request,
                         _("Investor '%s' was deleted successfully.") %
                         self.object.name)
        return reverse('dashboard:Investor-list')


# =============
# Investor users
# =============


class InvestorUserCreateView(generic.CreateView):
    model = User
    template_name = 'dashboard/investors/investor_user_form.html'
    form_class = NewUserForm

    def dispatch(self, request, *args, **kwargs):
        self.investor = get_object_or_404(
            Investor, pk=kwargs.get('investor_pk', None))
        return super(InvestorUserCreateView, self).dispatch(
            request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super(InvestorUserCreateView, self).get_context_data(**kwargs)
        ctx['investor'] = self.investor
        ctx['title'] = _('Create user')
        return ctx

    def get_form_kwargs(self):
        kwargs = super(InvestorUserCreateView, self).get_form_kwargs()
        kwargs['investor'] = self.investor
        return kwargs

    def get_success_url(self):
        name = self.object.get_full_name() or self.object.email
        messages.success(self.request,
                         _("User '%s' was created successfully.") % name)
        return reverse('dashboard:investor-list')


class InvestorUserSelectView(generic.ListView):
    template_name = 'dashboard/investors/investor_user_select.html'
    form_class = UserEmailForm
    context_object_name = 'users'

    def dispatch(self, request, *args, **kwargs):
        self.investor = get_object_or_404(
            Investor, pk=kwargs.get('investor_pk', None))
        return super(InvestorUserSelectView, self).dispatch(
            request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        data = None
        if 'email' in request.GET:
            data = request.GET
        self.form = self.form_class(data)
        return super(InvestorUserSelectView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super(InvestorUserSelectView, self).get_context_data(**kwargs)
        ctx['investor'] = self.investor
        ctx['form'] = self.form
        return ctx

    def get_queryset(self):
        if self.form.is_valid():
            email = normalise_email(self.form.cleaned_data['email'])
            return User.objects.filter(email__icontains=email)
        else:
            return User.objects.none()


class InvestorUserLinkView(generic.View):

    def get(self, request, user_pk, investor_pk):
        # need to allow GET to make Undo link in InvestorUserUnlinkView work
        return self.post(request, user_pk, investor_pk)

    def post(self, request, user_pk, investor_pk):
        user = get_object_or_404(User, pk=user_pk)
        name = user.get_full_name() or user.email
        investor = get_object_or_404(Investor, pk=investor_pk)
        if self.link_user(user, investor):
            messages.success(
                request,
                _("User '%(name)s' was linked to '%(investor_name)s'")
                % {'name': name, 'investor_name': investor.name})
        else:
            messages.info(
                request,
                _("User '%(name)s' is already linked to '%(investor_name)s'")
                % {'name': name, 'investor_name': investor.name})
        return redirect('dashboard:investor-manage', pk=investor_pk)

    def link_user(self, user, investor):
        """
        Links a user to a investor, and adds the dashboard permission if needed.

        Returns False if the user was linked already; True otherwise.
        """
        if investor.users.filter(pk=user.pk).exists():
            return False
        investor.users.add(user)
        if not user.is_staff:
            dashboard_access_perm = Permission.objects.get(
                codename='dashboard_access',
                content_type__app_label='investor')
            user.user_permissions.add(dashboard_access_perm)
        return True


class InvestorUserUnlinkView(generic.View):

    def unlink_user(self, user, investor):
        """
        Unlinks a user from a investor, and removes the dashboard permission
        if they are not linked to any other investors.

        Returns False if the user was not linked to the investor; True
        otherwise.
        """
        if not investor.users.filter(pk=user.pk).exists():
            return False
        investor.users.remove(user)
        if not user.is_staff and not user.investors.exists():
            dashboard_access_perm = Permission.objects.get(
                codename='dashboard_access',
                content_type__app_label='investor')
            user.user_permissions.remove(dashboard_access_perm)
        return True

    def post(self, request, user_pk, investor_pk):
        user = get_object_or_404(User, pk=user_pk)
        name = user.get_full_name() or user.email
        investor = get_object_or_404(Investor, pk=investor_pk)
        if self.unlink_user(user, investor):
            msg = render_to_string(
                'dashboard/investors/messages/user_unlinked.html',
                {'user_name': name,
                 'investor_name': investor.name,
                 'user_pk': user_pk,
                 'investor_pk': investor_pk})
            messages.success(self.request, msg, extra_tags='safe noicon')
        else:
            messages.error(
                request,
                _("User '%(name)s' is not linked to '%(investor_name)s'") %
                {'name': name, 'investor_name': investor.name})
        return redirect('dashboard:investor-manage', pk=investor_pk)


# =====
# Users
# =====


class InvestorUserUpdateView(generic.UpdateView):
    template_name = 'dashboard/investors/investor_user_form.html'
    form_class = ExistingUserForm

    def get_object(self, queryset=None):
        self.investor = get_object_or_404(Investor, pk=self.kwargs['investor_pk'])
        return get_object_or_404(User,
                                 pk=self.kwargs['user_pk'],
                                 investors__pk=self.kwargs['investor_pk'])

    def get_context_data(self, **kwargs):
        ctx = super(InvestorUserUpdateView, self).get_context_data(**kwargs)
        name = self.object.get_full_name() or self.object.email
        ctx['investor'] = self.investor
        ctx['title'] = _("Edit user '%s'") % name
        return ctx

    def get_success_url(self):
        name = self.object.get_full_name() or self.object.email
        messages.success(self.request,
                         _("User '%s' was updated successfully.") % name)
        return reverse('dashboard:investor-list')


class InvestmentCreateView(generic.CreateView):
    model = Investment
    template_name = 'dashboard/investors/investment_form.html'
    form_class = InvestmentCreateForm
    #success_url = reverse_lazy('dashboard:investor-list')

    def get_context_data(self, **kwargs):
        ctx = super(InvestmentCreateView, self).get_context_data(**kwargs)
        ctx['title'] = _('Create new investment')
        return ctx

    def get_initial(self):
        #initial = super(NewBankAccountCreateView, self).get_initial()
        initial = dict()
        initial['owners'] = (self.request.user,)
        initial['request'] = self.request
        initial['prospectus'] = CompanyProspectus.objects.get(pk=self.kwargs['pk'])
        return initial

    def get_success_url(self):
        messages.success(self.request,
                         _("Investment was created successfully."))
        return reverse('dashboard:company-prospectus-detail',
                       kwargs={'company_pk':self.kwargs['company_pk'], 'pk': self.kwargs['pk']})

class InvestorOrderView(generic.ListView):
    """
    This multi-purpose view renders out a form to edit the company's details,
    the associated address and a list of all associated users.
    """
    searchform_class = OrderSearchForm
    template_name = 'dashboard/investors/investor_orders.html'

    def get_queryset(self):
        return None

    def get_context_data(self, **kwargs):
        ctx = super(InvestorOrderView, self).get_context_data(**kwargs)
        if(self.request):
            ctx['current_user'] = self.request.user
            my_companys = []
            orders = []
            companys = Investor.objects.all()
            for company in companys:
                if (self.request.user in company.users.all()):
                    my_companys.append(company)
            for company in my_companys:
                for user in company.users.all():
                    orders += (Order.objects.filter(user=user))
            ctx['orders'] = orders
            ctx['searchform'] = self.searchform_class()
        return ctx



class InvestmentCommentsCreateView(generic.CreateView):
    model = InvestmentComment
    template_name = 'dashboard/investors/investment_comments_form.html'
    form_class = InvestmentCommentsCreateForm
    #success_url = reverse_lazy('dashboard:investor-list')

    def get_context_data(self, **kwargs):
        ctx = super(InvestmentCommentsCreateView, self).get_context_data(**kwargs)
        ctx['title'] = _('Create new investment comment')
        return ctx

    def get_initial(self):
        #initial = super(NewBankAccountCreateView, self).get_initial()
        initial = dict()
        initial['owners'] = (self.request.user,)
        initial['request'] = self.request
        initial['investment'] = Investment.objects.get(pk=self.kwargs['pk'])
        return initial

    def get_success_url(self):
        messages.success(self.request,
                         _("A new investment comment was created successfully."))
        return reverse('dashboard:company-prospectus-detail',
                       kwargs={'company_pk':self.kwargs['company_pk'], 'pk': self.kwargs['prospectus_pk']})


class InvestorMembersView(generic.ListView):
    """
    This multi-purpose view renders out a form to edit the company's details,
    the associated address and a list of all associated users.
    """
    template_name = 'dashboard/investors/investor_members.html'
    model = Investor
    success_url = reverse_lazy('dashboard:investor-list')

    def get_queryset(self):
        return None

    def get_context_data(self, **kwargs):
        ctx = super(InvestorMembersView, self).get_context_data(**kwargs)
        if(self.request):
            ctx['current_user'] = self.request.user
            my_investors = []
            investors = Investor.objects.all()
            for investor in investors:
                if (self.request.user in investor.users.all()):
                    my_investors.append(investor)
            ctx['investor'] = my_investors[0]
            ctx['users'] = my_investors[0].users.all()
        return ctx

class ProjectAnnouncementListView(generic.ListView):
    model = ProjectAnnouncement
    context_object_name = 'projectannouncements'
    template_name = 'dashboard/investors/project_announcement_list.html'
    form_class = ProjectAnnouncementSearchForm

    def get_queryset(self):
        qs = self.model._default_manager.all()
        qs = sort_queryset(qs, self.request, ['title'])

        self.description = _("All Project Announcements")

        # We track whether the queryset is filtered to determine whether we
        # show the search form 'reset' button.
        self.is_filtered = False
        self.form = self.form_class(self.request.GET)
        if not self.form.is_valid():
            return qs

        data = self.form.cleaned_data

        if data['title']:
            qs = qs.filter(title__icontains=data['title'])
            self.description = _("Project Announcements matching '%s'") % data['title']
            self.is_filtered = True

        return qs

    def get_context_data(self, **kwargs):
        ctx = super(ProjectAnnouncementListView, self).get_context_data(**kwargs)
        ctx['queryset_description'] = self.description
        ctx['form'] = self.form
        ctx['is_filtered'] = self.is_filtered
        my_investors = []
        investors = Investor.objects.all()
        for investor in investors:
            if (self.request.user in investor.users.all()):
                my_investors.append(investor)
        ctx['investor'] = my_investors[0]
        return ctx

class ProjectAnnouncementCreateView(generic.CreateView):
    model = ProjectAnnouncement
    template_name = 'dashboard/investors/project_announcement_form.html'
    form_class = ProjectAnnouncementCreateForm
    #success_url = reverse_lazy('dashboard:company-manage')

    def get_context_data(self, **kwargs):
        ctx = super(ProjectAnnouncementCreateView, self).get_context_data(**kwargs)
        ctx['title'] = _('Create new project announcement')
        ctx['investor_pk'] = self.kwargs['investor_pk']
        return ctx

    def get_success_url(self):
        messages.success(self.request,
                         _("Project announcement '%s' was created successfully.") %
                         self.object.title)
        return reverse('dashboard:investor-manage',
                       kwargs={'pk': self.kwargs['investor_pk']})

class ProjectAnnouncementDetailView(generic.DetailView):
    model = ProjectAnnouncement
    template_name = 'dashboard/investors/project_announcement_detail.html'

    def get_context_data(self, **kwargs):
        ctx = super(ProjectAnnouncementDetailView, self).get_context_data(**kwargs)
        ctx['title'] = _('Detail of Project Announcement')
        ctx['investor_pk'] = self.kwargs['investor_pk']
        ctx['projectannouncement'] = ProjectAnnouncement.objects.get(pk=self.kwargs['pk'])
        ctx['projecttenders'] = None
        ctx['is_investor'] = False
        ctx['projecttender_comments'] = None
        '''
        check = self.request.user.has_perm('investor.dashboard_access')
        if check:
            ctx['is_investor'] = True
            projecttenders = ProjectTender.objects.filter(projectannouncement=ctx['projectannouncement'])
            ctx['projecttenders'] = projecttenders.filter(user=self.request.user)
            if(len(ctx['projecttenders'])):
                ctx['projecttender_comments'] = ProjectTenderComment.objects.filter(investment=ctx['projecttenders'][0])

        check = self.request.user.has_perm('company.dashboard_access')
        if check:
            ctx['comments_list'] = []
            ctx['investments'] = Investment.objects.filter(prospectus=ctx['prospectus'])
            for investment in ctx['investments']:
                comments = InvestmentComment.objects.filter(investment=investment)
                ctx['comments_list'].append((investment, comments))

        '''

        return ctx