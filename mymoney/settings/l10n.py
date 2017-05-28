from .base import *

LANGUAGE_CODE = '<LANGUAGE_CODE>'
USE_I18N = True
USE_L10N = True

# Be sure to set it to True only if you have an available minify file generated
# with gulp at : mymoney/static/dist/<TYPE>/mymoney.min.<LANGUAGE_CODE>.<TYPE>
MYMONEY['USE_L10N_DIST'] = False
# You should see the list of available languages for each libraries.
# mymoney/static/bower_components/bootstrap-calendar/js/language/<LANGCODE>.js
MYMONEY['BOOTSTRAP_CALENDAR_LANGCODE'] = '<LANGUAGE_CODE>'
# mymoney/static/bower_components/bootstrap-datepicker/js/locales/bootstrap-datepicker.<LANGCODE>.js
MYMONEY['BOOTSTRAP_DATEPICKER_LANGCODE'] = '<LANGUAGE_CODE>'
