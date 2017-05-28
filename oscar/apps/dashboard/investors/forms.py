from django import forms
from django.contrib.auth.models import Permission
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import pgettext_lazy

from oscar.apps.customer.forms import EmailUserCreationForm
from oscar.core.compat import existing_user_fields, get_user_model
from oscar.core.loading import get_model
from oscar.core.validators import password_validators
from oscar.forms.widgets import ImageInput

User = get_user_model()
Investor = get_model('investor', 'Investor')
InvestorAddress = get_model('investor', 'InvestorAddress')
Investment = get_model('investor', 'Investment')
InvestmentComment = get_model('investor', 'InvestmentComment')
ProjectAnnouncement = get_model('investor', 'ProjectAnnouncement')

class InvestorSearchForm(forms.Form):
    name = forms.CharField(
        required=False, label=pgettext_lazy(u"Investor's name", u"Name"))


class InvestorCreateForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(InvestorCreateForm, self).__init__(*args, **kwargs)
        # Investor.name is optional and that is okay. But if creating through
        # the dashboard, it seems sensible to enforce as it's the only field
        # in the form.
        self.fields['name'].required = True

    class Meta:
        model = Investor
        fields = ('name',)

ROLE_CHOICES = (
    ('staff', _('Full dashboard access')),
    ('limited', _('Limited dashboard access')),
)


class NewUserForm(EmailUserCreationForm):
    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.RadioSelect,
                             label=_('User role'), initial='limited')

    def __init__(self, investor, *args, **kwargs):
        self.investor = investor
        super(NewUserForm, self).__init__(host=None, *args, **kwargs)

    def save(self):
        role = self.cleaned_data.get('role', 'limited')
        user = super(NewUserForm, self).save(commit=False)
        user.is_staff = role == 'staff'
        user.save()
        self.investor.users.add(user)
        if role == 'limited':
            dashboard_access_perm = Permission.objects.get(
                codename='dashboard_access', content_type__app_label='investor')
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
            codename='dashboard_access', content_type__app_label='investor')
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


class InvestorAddressForm(forms.ModelForm):
    name = forms.CharField(
        required=False, max_length=128,
        label=pgettext_lazy(u"Investor's name", u"Name"))

    class Meta:
        fields = ('name', 'line1', 'line2', 'line3', 'line4',
                  'state', 'postcode', 'country')
        model = InvestorAddress


class InvestmentCreateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', None)
        self.request = None
        if initial:
            self.request = initial.get('request', None)
            self.prospectus = initial.get('prospectus', None)
        super(InvestmentCreateForm, self).__init__(*args, **kwargs)
        # Investor.name is optional and that is okay. But if creating through
        # the dashboard, it seems sensible to enforce as it's the only field
        # in the form.
        self.fields['amount'].required = True

    def save(self, *args, **kwargs):
        #self.cleaned_data['user'] = self.request.user
        #self.cleaned_data['prospectus'] = self.prospectus
        obj = super(InvestmentCreateForm, self).save(*args, **kwargs)
        obj.user = self.request.user
        obj.prospectus = self.prospectus
        investors = Investor.objects.all()
        for investor in investors:
            if self.request.user in investor.users.all():
                obj_investor = investor
                break
        obj.investor = obj_investor
        obj.save()

    class Meta:
        model = Investment
        fields = ('amount', )

class InvestmentCommentsCreateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', None)
        self.request = None
        if initial:
            self.request = initial.get('request', None)
            self.investment = initial.get('investment', None)
        super(InvestmentCommentsCreateForm, self).__init__(*args, **kwargs)
        # Investor.name is optional and that is okay. But if creating through
        # the dashboard, it seems sensible to enforce as it's the only field
        # in the form.
        self.fields['comment'].required = True

    def save(self, *args, **kwargs):
        #self.cleaned_data['user'] = self.request.user
        #self.cleaned_data['prospectus'] = self.prospectus
        obj = super(InvestmentCommentsCreateForm, self).save(*args, **kwargs)
        obj.user = self.request.user
        obj.investment = self.investment
        obj.save()

    class Meta:
        model = InvestmentComment
        fields = ('comment', )

class ProjectAnnouncementCreateForm(forms.ModelForm):
    #image = forms.ImageField()

    def __init__(self, *args, **kwargs):
        super(ProjectAnnouncementCreateForm, self).__init__(*args, **kwargs)
        # Company.name is optional and that is okay. But if creating through
        # the dashboard, it seems sensible to enforce as it's the only field
        # in the form.
        self.fields['title'].required = True

    class Meta:
        model = ProjectAnnouncement
        fields = ('title', 'investor', 'proposal', 'scale_of_funding', 'share_ratio', 'proposal_details', 'status', )

class ProjectAnnouncementSearchForm(forms.Form):
    title = forms.CharField(
        required=False, label=pgettext_lazy(u"Project Announcement's title", u"Title"))
