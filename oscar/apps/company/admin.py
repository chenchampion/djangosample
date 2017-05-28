from django.contrib import admin

from oscar.core.loading import get_model

Company = get_model('company', 'Company')

CompanyProspectus = get_model('company', 'CompanyProspectus')

admin.site.register(Company)
admin.site.register(CompanyProspectus)
