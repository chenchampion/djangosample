from django.conf import settings
from django.test import TestCase, modify_settings
from django.urls import reverse

from mymoney.apps.bankaccounts.factories import BankAccountFactory
from mymoney.mymoneycore.factories import UserFactory

from ..factories import BankTransactionTagFactory


@modify_settings(MIDDLEWARE={
    'remove': ['mymoney.mymoneycore.middleware.AnonymousRedirectMiddleware'],
})
class AccessTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.owner = UserFactory(username='owner')
        cls.not_owner = UserFactory(username='not_owner', user_permissions='staff')
        cls.not_strict_owner = UserFactory(username='not_strict_owner', user_permissions='staff')
        cls.superowner = UserFactory(username='superowner', user_permissions='admin')
        cls.bankaccount = BankAccountFactory(owners=[
            cls.owner, cls.not_strict_owner, cls.superowner
        ])

        cls.banktransactiontag = BankTransactionTagFactory(owner=cls.superowner)

    def test_access_list(self):
        url = reverse('banktransactiontags:list')

        # Anonymous redirected
        response = self.client.get(url)
        self.assertRedirects(response,
                             reverse(settings.LOGIN_URL) + '?next=' + url)

        # Authenticated.
        self.client.force_login(self.owner)
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

    def test_access_create(self):
        url = reverse('banktransactiontags:create')

        # Missing permission.
        self.client.force_login(self.owner)
        response = self.client.get(url)
        self.assertEqual(403, response.status_code)
        self.client.logout()

        # With permission.
        self.client.force_login(self.superowner)
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        self.client.logout()

    def test_access_update(self):
        url = reverse('banktransactiontags:update', kwargs={
            'pk': self.banktransactiontag.pk
        })

        # Anonymous
        response = self.client.get(url)
        self.assertEqual(403, response.status_code)

        # Non-owner at all with permissions.
        self.client.force_login(self.not_owner)
        response = self.client.get(url)
        self.assertEqual(403, response.status_code)
        self.client.logout()

        # Not strict owner with permissions.
        self.client.force_login(self.not_strict_owner)
        response = self.client.get(url)
        self.assertEqual(403, response.status_code)
        self.client.logout()

        # Owner with permissions
        self.client.force_login(self.superowner)
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        self.client.logout()

        # Fake bank transaction tag.
        url = reverse('banktransactiontags:update', kwargs={
            'pk': 20140923
        })
        self.client.force_login(self.superowner)
        response = self.client.get(url)
        self.assertEqual(404, response.status_code)
        self.client.logout()

    def test_access_delete(self):
        url = reverse('banktransactiontags:delete', kwargs={
            'pk': self.banktransactiontag.pk
        })

        # Anonymous
        response = self.client.get(url)
        self.assertEqual(403, response.status_code)

        # Non-owner with permissions.
        self.client.force_login(self.not_owner)
        response = self.client.get(url)
        self.assertEqual(403, response.status_code)
        self.client.logout()

        # Not strict owner with permissions.
        self.client.force_login(self.not_strict_owner)
        response = self.client.get(url)
        self.assertEqual(403, response.status_code)
        self.client.logout()

        # Owner with permissions
        self.client.force_login(self.superowner)
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        self.client.logout()


class ViewTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.owner = UserFactory(username='owner')
        cls.not_owner = UserFactory(username='not_owner', user_permissions='staff')
        cls.superowner = UserFactory(username='superowner', user_permissions='admin')
        cls.bankaccount = BankAccountFactory(owners=[cls.owner, cls.superowner])

        cls.banktransactiontags = [
            BankTransactionTagFactory(owner=cls.owner),
            BankTransactionTagFactory(owner=cls.owner),
            BankTransactionTagFactory(owner=cls.not_owner),
            BankTransactionTagFactory(owner=cls.superowner),
        ]

    def test_list_view(self):

        self.client.force_login(self.owner)
        response = self.client.get(reverse('banktransactiontags:list'))
        ids = sorted(list((response.context_data['banktransactiontag_list']
                           .values_list('pk', flat=True))))
        self.assertListEqual(
            [
                self.banktransactiontags[0].pk,
                self.banktransactiontags[1].pk,
                self.banktransactiontags[3].pk,
            ],
            ids,
        )
