from django.contrib import admin

from oscar.core.loading import get_model

Investor = get_model('investor', 'Investor')
Investment = get_model('investor', 'Investment')

admin.site.register(Investor)
admin.site.register(Investment)
