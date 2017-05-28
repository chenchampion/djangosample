#-*- coding: UTF-8 -*-
from django.contrib.auth.models import AbstractUser
from django.db import models
import datetime
#from pioneers.models import Pioneer
#from vendors.models import Vendor

class CustomUser(AbstractUser):
    birth_date = models.DateField(null=True, blank=True)
    title = models.CharField('title', max_length=64,blank=True)
    isCreator = models.BooleanField('Do you want to found a new Org?', default=False, blank=True)
    '''
    company = models.ForeignKey(
        Pioneer,
        verbose_name=('所属研发公司'),
        blank=True, null=True,
        help_text=(
            'The group this user belongs to.'
        ),
        related_name="user_set",
        related_query_name="user",
    )

    vendor = models.ForeignKey(
        Vendor,
        verbose_name=('所属供应商公司'),
        blank=True, null=True,
        help_text=(
            'The group this user belongs to.'
        ),
        related_name="user_set",
        related_query_name="user",
    )
    '''

def get_custom_anon_user(User):
    return User(
        username='AnonymousUser',
        birth_date=datetime.date(1410, 7, 15),
    )
