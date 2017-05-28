from oscar.apps.address.abstract_models import AbstractInvestorAddress
from oscar.apps.investor.abstract_models import (
    AbstractInvestor, AbstractInvestment, AbstractInvestmentComment, AbstractProjectAnnouncement)
from oscar.core.loading import is_model_registered

__all__ = []


if not is_model_registered('investor', 'Investor'):
    class Investor(AbstractInvestor):
        pass

    __all__.append('Investor')


if not is_model_registered('investor', 'InvestorAddress'):
    class InvestorAddress(AbstractInvestorAddress):
        pass

    __all__.append('InvestorAddress')


if not is_model_registered('investor', 'Investment'):
    class Investment(AbstractInvestment):
        pass

    __all__.append('Investment')

if not is_model_registered('investor', 'InvestmentComment'):
    class InvestmentComment(AbstractInvestmentComment):
        pass

    __all__.append('InvestmentComment')

if not is_model_registered('investor', 'ProjectAnnouncement'):
    class ProjectAnnouncement(AbstractProjectAnnouncement):
        pass

    __all__.append('ProjectAnnouncement')