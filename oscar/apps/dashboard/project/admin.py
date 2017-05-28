from django.contrib import admin
from . import models

# Register your models here.
admin.site.register(models.SubscribedUser)
admin.site.register(models.InvitedUser)
admin.site.register(models.Task)
admin.site.register(models.Project)
admin.site.register(models.LinkedProject)
