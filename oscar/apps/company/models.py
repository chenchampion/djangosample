from oscar.apps.address.abstract_models import AbstractCompanyAddress
from oscar.apps.company.abstract_models import  AbstractCompany, AbstractCompanyProspectus
from oscar.core.loading import is_model_registered

__all__ = []


if not is_model_registered('company', 'Company'):
    class Company(AbstractCompany):
        pass

    __all__.append('Company')


if not is_model_registered('Company', 'CompanyAddress'):
    class CompanyAddress(AbstractCompanyAddress):
        pass

    __all__.append('CompanyAddress')


if not is_model_registered('Company', 'CompanyProspectus'):
    class CompanyProspectus(AbstractCompanyProspectus):
        pass

    __all__.append('CompanyProspectus')

