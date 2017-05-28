from django import forms
from django.contrib.auth.models import Permission
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import pgettext_lazy

from oscar.apps.customer.forms import EmailUserCreationForm
from oscar.core.compat import existing_user_fields, get_user_model
from oscar.core.loading import get_model
from oscar.core.validators import password_validators
from mymoney.apps.bankaccounts.models import BankAccount
from oscar.apps.dashboard.project.models import Project
from .models import TaskExpense
from oscar.apps.dashboard.project.helpers import get_project

User = get_user_model()
Company = get_model('company', 'Company')
CompanyAddress = get_model('company', 'CompanyAddress')


class CompanySearchForm(forms.Form):
    name = forms.CharField(
        required=False, label=pgettext_lazy(u"Company's name", u"Name"))


class BankAccountCreateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', None)
        self.request = None
        if initial:
            self.request = initial.get('request', None)
        super(BankAccountCreateForm, self).__init__(*args, **kwargs)

        # Company.name is optional and that is okay. But if creating through
        # the dashboard, it seems sensible to enforce as it's the only field
        # in the form.
        self.fields['project'].required = True
        if self.request:
            self.fields['owners'].queryset = User.objects.filter(username=self.request.user.username)
            self.fields['project'].queryset = Project.objects.filter(owner=self.request.user.id)
    class Meta:
        model = BankAccount
        fields = ('project', 'label', 'balance_initial', 'currency', 'owners')

class TaskExpenseCreateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', None)
        self.request = None
        if initial:
            self.request = initial.get('request', None)
            self.project_name = initial.get('project_name', None)
        super(TaskExpenseCreateForm, self).__init__(*args, **kwargs)
        if self.request:
            project = get_project(self.request, self.project_name)
            self.fields['task'].queryset = project.task_set.all()
            self.fields['bankaccount'].queryset = project.bankaccount_set.all()

            #self.fields['owners'].queryset = User.objects.filter(username=self.request.user.username)
            #self.fields['project'].queryset = project
    class Meta:
        model = TaskExpense
        fields = ('bankaccount', 'date', 'amount', 'task', 'payment_method', 'memo')




class CompanyCreateForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(CompanyCreateForm, self).__init__(*args, **kwargs)
        # Company.name is optional and that is okay. But if creating through
        # the dashboard, it seems sensible to enforce as it's the only field
        # in the form.
        self.fields['name'].required = True

    class Meta:
        model = Company
        fields = ('name',)

ROLE_CHOICES = (
    ('staff', _('Full dashboard access')),
    ('limited', _('Limited dashboard access')),
)


class NewUserForm(EmailUserCreationForm):
    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.RadioSelect,
                             label=_('User role'), initial='limited')

    def __init__(self, company, *args, **kwargs):
        self.company = company
        super(NewUserForm, self).__init__(host=None, *args, **kwargs)

    def save(self):
        role = self.cleaned_data.get('role', 'limited')
        user = super(NewUserForm, self).save(commit=False)
        user.is_staff = role == 'staff'
        user.save()
        self.company.users.add(user)
        if role == 'limited':
            dashboard_access_perm = Permission.objects.get(
                codename='dashboard_access', content_type__app_label='company')
            user.user_permissions.add(dashboard_access_perm)
        return user

    class Meta:
        model = User
        fields = existing_user_fields(
            ['first_name', 'last_name', 'email']) + ['password1', 'password2']


class ExistingUserForm(forms.ModelForm):
    """
    Slightly different form that makes
    * makes saving password optional
    * doesn't regenerate username
    * doesn't allow changing email till #668 is resolved
    """
    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.RadioSelect,
                             label=_('User role'))
    password1 = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput,
        required=False,
        validators=password_validators)
    password2 = forms.CharField(
        required=False,
        label=_('Confirm Password'),
        widget=forms.PasswordInput)

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1', '')
        password2 = self.cleaned_data.get('password2', '')

        if password1 != password2:
            raise forms.ValidationError(
                _("The two password fields didn't match."))
        return password2

    def __init__(self, *args, **kwargs):
        user = kwargs['instance']
        role = 'staff' if user.is_staff else 'limited'
        kwargs.get('initial', {}).setdefault('role', role)
        super(ExistingUserForm, self).__init__(*args, **kwargs)

    def save(self):
        role = self.cleaned_data.get('role', 'none')
        user = super(ExistingUserForm, self).save(commit=False)
        user.is_staff = role == 'staff'
        if self.cleaned_data['password1']:
            user.set_password(self.cleaned_data['password1'])
        user.save()

        dashboard_perm = Permission.objects.get(
            codename='dashboard_access', content_type__app_label='company')
        user_has_perm = user.user_permissions.filter(
            pk=dashboard_perm.pk).exists()
        if role == 'limited' and not user_has_perm:
            user.user_permissions.add(dashboard_perm)
        elif role == 'staff' and user_has_perm:
            user.user_permissions.remove(dashboard_perm)
        return user

    class Meta:
        model = User
        fields = existing_user_fields(
            ['first_name', 'last_name']) + ['password1', 'password2']


class UserEmailForm(forms.Form):
    # We use a CharField so that a partial email address can be entered
    email = forms.CharField(
        label=_("Email address"), max_length=100)


class CompanyAddressForm(forms.ModelForm):
    name = forms.CharField(
        required=False, max_length=128,
        label=pgettext_lazy(u"Company's name", u"Name"))

    class Meta:
        fields = ('name', 'line1', 'line2', 'line3', 'line4',
                  'state', 'postcode', 'country')
        model = CompanyAddress
