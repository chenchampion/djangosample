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
from oscar.apps.dashboard.project.models import Project
from models import TaskExpense
from decimal import Decimal

User = get_user_model()
Company = get_model('company', 'Company')
(
    CompanySearchForm, CompanyCreateForm, CompanyAddressForm,
    NewUserForm, UserEmailForm, ExistingUserForm
) = get_classes(
    'dashboard.companys.forms',
    ['CompanySearchForm', 'CompanyCreateForm', 'CompanyAddressForm',
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

from django.contrib.auth.mixins import (
    LoginRequiredMixin, PermissionRequiredMixin,
)
from mymoney.apps.banktransactions.mixins import BankTransactionAccessMixin
from mymoney.apps.banktransactionanalytics.mixins import RatioViewMixin, TrendTimeViewMixin
from mymoney.apps.banktransactionanalytics.forms import RatioForm, TrendtimeForm
from django.db.models import Count, Max, Min, QuerySet, Sum
from  mymoney.apps.bankaccounts.mixins import BankAccountAccessMixin, BankAccountSaveFormMixin
from mymoney.apps.bankaccounts.models import BankAccount
from django.contrib.messages.views import SuccessMessageMixin
import random
import json
from django.utils.functional import cached_property
from .forms import *

class RatioView(BankTransactionAccessMixin, RatioViewMixin, generic.FormView):

    template_name = 'banktransactionanalytics/ratio/overview.html'
    form_class = RatioForm

    def get_initial(self):
        initial = super(RatioView, self).get_initial()
        initial.update(self.session_data.get('filters', {}))
        initial.update(self.session_data.get('raw_input', {}))
        return initial

    def get_form_kwargs(self):
        kwargs = super(RatioView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        self.success_url = reverse('banktransactionanalytics:ratio', kwargs={
            'bankaccount_pk': self.bankaccount.pk,
        })
        return super(RatioView, self).get_success_url()

    def post(self, request, *args, **kwargs):

        # Skip any validations for reset action.
        if request.POST.get('reset', False):
            return self.form_valid(self.get_form())

        return super(RatioView, self).post(request, *args, **kwargs)

    def form_valid(self, form):

        if 'filter' in self.request.POST:
            filters, raw_input = {}, {}
            session_data = self.session_data

            for key, value in form.cleaned_data.items():
                value = list(value) if isinstance(value, QuerySet) else value

                if value in form.fields[key].empty_values:
                    continue

                if key == 'tags':
                    data = [tag.pk for tag in value]
                elif key.startswith('date_') or key.startswith('sum_'):
                    data = str(value)
                    raw_input[key] = self.request.POST.get(key, None)
                else:
                    data = value

                filters[key] = data

            session_data['filters'] = filters
            session_data['raw_input'] = raw_input
            self.session_data = session_data

        elif 'reset' in self.request.POST:  # pragma: no branch
            del self.session_data

        return super(RatioView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(RatioView, self).get_context_data(**kwargs)
        context['bankaccount'] = self.bankaccount

        session_data = self.session_data
        filters = session_data.get('filters', {})
        session_data['colors'] = session_data.get('colors', {})

        # Filters are required to prevent huge data aggregation costs.
        context['has_filters'] = bool(filters)
        if context['has_filters']:

            total = self.total_queryset
            if total is not None:
                colors = self.colors.copy()

                rows, sub_total = [], 0
                for data in self.tag_queryset:
                    tag_id = str(data['tag']) if data['tag'] else '0'

                    if tag_id in session_data['colors']:
                        color = session_data['colors'][tag_id]
                    else:
                        color = colors.pop(colors.index(random.choice(colors)))
                        session_data['colors'][tag_id] = color
                        self.session_data = session_data

                    rows.append({
                        'tag_id': data['tag'],
                        'tag_name': data['tag__name'],
                        'sum': data['sum'],
                        'count': data['count'],
                        'percentage': round(data['sum'] * 100 / total, 2),
                        'color': color,
                        'color_rgba': 'rgba({r}, {g}, {b}, {a})'.format(
                            r=color[0],
                            g=color[1],
                            b=color[2],
                            a=0.7,
                        ),
                    })

                    sub_total += data['sum']

                context['rows'] = rows
                context['sub_total'] = sub_total
                context['total'] = total

                if rows:
                    context['chart_data'] = json.dumps({
                        'data': [
                            {
                                'label': row['tag_name'] if row['tag_name'] else _('no tag'),
                                'value': float(row['percentage']),
                                'color': row['color_rgba'],
                                'highlight': 'rgba({r}, {g}, {b}, {a})'.format(
                                    r=row['color'][0],
                                    g=row['color'][1],
                                    b=row['color'][2],
                                    a=0.6,
                                ),
                            } for row in rows
                        ],
                        'type': filters['chart'],
                    })

        return context

    @cached_property
    def base_queryset(self):

        qs = super(RatioView, self).base_queryset

        filters = self.session_data.get('filters', {})
        if filters['type'] in (RatioForm.SUM_CREDIT, RatioForm.SUM_DEBIT):

            qs = qs.values('tag', 'tag__name')
            qs = qs.annotate(sum=Sum('amount'))

            if filters['type'] == RatioForm.SUM_CREDIT:
                qs = qs.filter(sum__gt=0)
            else:
                qs = qs.filter(sum__lt=0)

        return qs

    @property
    def total_queryset(self):

        filters = self.session_data.get('filters', {})
        if filters['type'] in (RatioForm.SINGLE_CREDIT, RatioForm.SINGLE_DEBIT):
            field = 'amount'
        else:
            field = 'sum'

        return self.base_queryset.aggregate(total=Sum(field))['total']

    @property
    def tag_queryset(self):
        qs = self.base_queryset

        filters = self.session_data.get('filters', {})

        if 'tags' in filters:
            qs = qs.filter(tag__in=filters['tags'])

        # Always group result by tags.
        if filters['type'] in (RatioForm.SINGLE_CREDIT, RatioForm.SINGLE_DEBIT):
            qs = qs.values('tag', 'tag__name')
            qs = qs.annotate(sum=Sum('amount'))

        qs = qs.annotate(count=Count('id'))

        if 'sum_min' in filters and 'sum_max' in filters:
            qs = qs.filter(sum__range=(
                filters['sum_min'],
                filters['sum_max'],
            ))
        elif 'sum_min' in filters:
            qs = qs.filter(sum__gte=filters['sum_min'])
        elif 'sum_max' in filters:
            qs = qs.filter(sum__lte=filters['sum_max'])

        if filters['type'] in (RatioForm.SINGLE_DEBIT, RatioForm.SUM_DEBIT):
            qs = qs.order_by('sum')
        else:
            qs = qs.order_by('-sum')

        return qs

    @cached_property
    def colors(self):
        return [
            [66, 139, 202],     # some kind of blue
            [128, 0, 128],      # purle
            [265, 165, 0],      # orange
            [192, 192, 192],    # silver
            [0, 128, 0],        # green
            [250, 128, 114],    # saumon
            [255, 215, 0],      # gold
            [255, 0, 0],        # red
            [64, 224, 208],     # turquoise
            [182, 128, 128],    # gray
            [255, 255, 0],      # yellow
            [128, 0, 0],        # maroon
            [128, 128, 0],      # olive
            [255, 0, 255],      # fuchsia
            [0, 255, 0],        # lime
            [0, 128, 128],      # teal
            [0, 128, 128],      # navy
            [255, 192, 203],    # pink
            [245, 222, 179],    # wheat
            [173, 216, 230],    # lightblue
            [0, 255, 255],      # aqua
            [220, 20, 60],      # crimson
        ]

class BankAccountListView(generic.ListView):
    model = BankAccount
    template_name = 'dashboard/money/bankaccount_list.html'

    def get_queryset(self):
        return BankAccount.objects.get_user_bankaccounts(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super(BankAccountListView, self).get_context_data(**kwargs)
        ctx['bankaccounts'] = []
        for bankaccount in ctx['object_list']:
            taskexpenses = bankaccount.taskexpenses.all()
            balance = bankaccount.balance_initial
            for expense in taskexpenses:
                balance -= expense.amount
            tasks = bankaccount.project.task_set.all()
            for task in tasks:
                if(task.order):
                    balance -= task.order.total_incl_tax
            ctx['bankaccounts'].append((bankaccount, balance))
        return ctx

class NewBankAccountCreateView(generic.CreateView):
    model = BankAccount
    template_name = 'dashboard/money/bankaccount_form.html'
    form_class = BankAccountCreateForm
    success_url = reverse_lazy('dashboard:company-list')

    def get_initial(self):
        #initial = super(NewBankAccountCreateView, self).get_initial()
        initial = dict()
        initial['owners'] = (self.request.user,)
        initial['request'] = self.request
        return initial

    def get_context_data(self, **kwargs):
        ctx = super(NewBankAccountCreateView, self).get_context_data(**kwargs)
        ctx['title'] = _('Create Project Budget')
        return ctx

    def get_success_url(self):
        #messages.success(self.request,
                         #_("Company '%s' was created successfully.") %
                         #self.object.label)
        return reverse('dashboard:mymoney-list')

class BankAccountDeleteView(generic.DeleteView):
    model = BankAccount
    template_name = 'dashboard/money/bankaccount_delete.html'
    success_url = reverse_lazy('dashboard:company-list')

class BankAccountUpdateView(generic.UpdateView):
    model = BankAccount
    fields = ['project', 'label', 'balance', 'balance_initial', 'currency']
    template_name = 'dashboard/money/bankaccount_update_form.html'
    #success_message = _("Bank account %(label)s was updated successfully")

class DecimalEncoder(json.JSONEncoder):
    def _iterencode(self, o, markers=None):
        if isinstance(o, Decimal):
            # wanted a simple yield str(o) in the next line,
            # but that would mean a yield on the line with super(...),
            # which wouldn't work (see my comment below), so...
            return (str(o) for o in [o])
        return super(DecimalEncoder, self)._iterencode(o, markers)

class ExpenseListView(generic.ListView):
    model = TaskExpense
    template_name = 'dashboard/money/project_expenses_list.html'

    #def get_queryset(self):
        #bankaccount = BankAccount.objects.get(pk=self.kwargs['pk'])
        #return TaskExpense.objects.get_task_expense(self.request, bankaccount.project.name)

    def get_context_data(self, **kwargs):
        ctx = super(ExpenseListView, self).get_context_data(**kwargs)
        ctx['bankaccount'] = BankAccount.objects.get(pk=self.kwargs['pk'])
        ctx['taskexpenses'] = ctx['bankaccount'].taskexpenses.all()
        balance = ctx['bankaccount'].balance_initial
        total_expense = Decimal(0.00)
        detail_expense = []
        for expense in ctx['taskexpenses']:
            balance -= expense.amount
            total_expense += expense.amount
        for expense in ctx['taskexpenses']:
            detail_expense.append([expense.memo, float(expense.amount/total_expense)])
        ctx['total_expense'] = total_expense/ctx['bankaccount'].balance_initial
        ctx['detail_expense'] = json.dumps(detail_expense)
        tasks = ctx['bankaccount'].project.task_set.all()
        orders = []
        total_order = Decimal(0.00)
        detail_order = []
        for task in tasks:
            if(task.order):
                orders.append((task, task.order))
                balance -= task.order.total_incl_tax
                total_order += task.order.total_incl_tax
        for task in tasks:
            if (task.order):
                detail_order.append([task.order.number, float(task.order.total_incl_tax/total_order)])
        ctx['orders'] = orders
        ctx['total_order'] = total_order/ctx['bankaccount'].balance_initial
        ctx['detail_order'] = json.dumps(detail_order)
        ctx['balance'] = balance
        ctx['balance_rate'] = balance/ctx['bankaccount'].balance_initial
        return ctx

class ExpenseCreateView(generic.CreateView):
    model = TaskExpense
    template_name = 'dashboard/money/taskexpense_form.html'
    form_class = TaskExpenseCreateForm
    success_url = reverse_lazy('dashboard:company-list')

    def get_initial(self):
        #initial = super(NewBankAccountCreateView, self).get_initial()
        initial = dict()
        initial['owners'] = (self.request.user,)
        initial['request'] = self.request
        initial['project_name'] = self.kwargs['name']
        return initial

    def get_context_data(self, **kwargs):
        ctx = super(ExpenseCreateView, self).get_context_data(**kwargs)
        ctx['title'] = _('Create Task Expense')
        ctx['bankaccount'] = BankAccount.objects.filter(pk=self.kwargs['pk'])
        return ctx

    def get_success_url(self):
        #messages.success(self.request,
                         #_("Company '%s' was created successfully.") %
                         #self.object.label)
        return reverse('dashboard:mymoney-expenselist',kwargs={"pk":self.kwargs['pk']})