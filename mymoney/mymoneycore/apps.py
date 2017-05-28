from django.apps import AppConfig


class MyMoneyConfig(AppConfig):
    name = 'mymoney.mymoneycore'
    verbose_name = "MyMoney"

    def ready(self):
        import mymoney.mymoneycore.checks  # noqa
