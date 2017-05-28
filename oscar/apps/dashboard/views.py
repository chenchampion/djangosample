from datetime import timedelta
from decimal import Decimal as D
from decimal import ROUND_UP

from django.db.models import Avg, Count, Sum
from django.utils.timezone import now
from django.views.generic import TemplateView

from oscar.apps.promotions.models import AbstractPromotion
from oscar.core.compat import get_user_model
from oscar.core.loading import get_model
from django.shortcuts import get_object_or_404, render
from django.db import models
from swingtime import utils, forms
from oscar.apps.dashboard.project.models import Project
ConditionalOffer = get_model('offer', 'ConditionalOffer')
Voucher = get_model('voucher', 'Voucher')
Basket = get_model('basket', 'Basket')
StockAlert = get_model('partner', 'StockAlert')
Product = get_model('catalogue', 'Product')
Order = get_model('order', 'Order')
Line = get_model('order', 'Line')
User = get_user_model()
Company = get_model('company', 'Company')
Investor = get_model('investor', 'Investor')
Partner = get_model('partner', 'Partner')
CompanyProspectus = get_model('company', 'CompanyProspectus')

import calendar
import itertools
from datetime import datetime, timedelta, time
from oscar.apps.dashboard.models import Event, Occurrence, EventType

class IndexView(TemplateView):
    """
    An overview view which displays several reports about the shop.

    Supports the permission-based dashboard. It is recommended to add a
    index_nonstaff.html template because Oscar's default template will
    display potentially sensitive store information.
    """

    def get_template_names(self):
        if self.request.user.is_staff:
            return ['dashboard/index.html', ]
        else:
            return ['dashboard/index_nonstaff.html', 'dashboard/index.html']

    def get_context_data(self, **kwargs):
        ctx = super(IndexView, self).get_context_data(**kwargs)
        ctx.update(self.get_stats())

        year, month = int(datetime.now().year), int(datetime.now().month)
        cal = calendar.monthcalendar(year, month)
        dtstart = datetime(year, month, 1)
        last_day = max(cal[-1])
        dtend = datetime(year, month, last_day)

        # TODO Whether to include those occurrences that started in the previous
        # month but end in this month?
        subs = []
        subs_projects = []
        if self.request.user:
            subs = self.request.user.subscribeduser_set.all()

        for sub in subs:
            subs_projects.append(sub.project)

        queryset_project = None
        queryset_project = queryset_project._clone() if queryset_project is not None else Project.objects.select_related()
        start_projects = queryset_project.filter(start_date__year=year, start_date__month=month)
        end_projects = queryset_project.filter(end_date__year=year, end_date__month=month)

        projects_start = set(start_projects) & set(subs_projects)
        projects_end = set(end_projects) & set(subs_projects)

        def start_pj_day(o):
            return o.start_date.day

        def end_pj_day(o):
            return o.end_date.day

        def start_task_day(o):
            return o.expected_start_date.day

        def end_task_day(o):
            return o.expected_end_date.day

        tasks_start = []
        tasks_end = []
        all_tasks = []
        for project in subs_projects:
            all_tasks += project.new_tasks()

        start_projects_day = dict([(dt, list(o)) for dt, o in itertools.groupby(projects_start, start_pj_day)])
        end_projects_day = dict([(dt, list(o)) for dt, o in itertools.groupby(projects_end, end_pj_day)])
        start_tasks_day = dict([(dt, list(o)) for dt, o in itertools.groupby(all_tasks, start_task_day)])
        end_tasks_day = dict([(dt, list(o)) for dt, o in itertools.groupby(all_tasks, end_task_day)])


        ctx['calendar'] = [[(d, start_projects_day.get(d, []), end_projects_day.get(d, []), start_tasks_day.get(d, []), end_tasks_day.get(d, [])) for d in row] for row in cal]
        ctx['today'] = datetime.now()
        ctx['today_events'] = [(ctx['today'], start_projects_day.get(ctx['today'], []), end_projects_day.get(ctx['today'], []), start_tasks_day.get(ctx['today'], []), end_tasks_day.get(ctx['today'], []))]
        ctx['this_month'] = dtstart
        ctx['next_month'] = dtstart + timedelta(days=+last_day)
        ctx['last_month'] = dtstart + timedelta(days=-1)
        ctx['last_year'] = (year - 1)
        ctx['next_year'] = (year + 1)

        ctx['user_group'] = True
        is_investor = self.request.user.has_perm('investor.dashboard_access')
        is_company = self.request.user.has_perm('company.dashboard_access')
        is_partner = self.request.user.has_perm('partner.dashboard_access')
        if self.request.user.is_staff:
            ctx['user_group'] = False
        elif is_investor:
            ctx['group_type'] = 1
            ctx['current_user'] = self.request.user
            my_investor = []
            investors = Investor.objects.all()
            for investor in investors:
                if (self.request.user in investor.users.all()):
                    my_investor.append(investor)
            ctx['investor'] = my_investor[0]
            ctx['prospectuses'] = CompanyProspectus.objects.filter(status='Active')
        elif is_company:
            ctx['group_type'] = 2
            ctx['current_user'] = self.request.user
            my_companys = []
            companys = Company.objects.all()
            for company in companys:
                if (self.request.user in company.users.all()):
                    my_companys.append(company)
            ctx['company'] = my_companys[0]
        elif is_partner:
            ctx['group_type'] = 3
            ctx['current_user'] = self.request.user
            my_partners = []
            partners = Partner.objects.all()
            for partner in partners:
                if (self.request.user in partner.users.all()):
                    my_partners.append(partner)
            ctx['partner'] = my_partners[0]
        else:
            ctx['user_group'] = False
        return ctx

    def get_active_site_offers(self):
        """
        Return active conditional offers of type "site offer". The returned
        ``Queryset`` of site offers is filtered by end date greater then
        the current date.
        """
        return ConditionalOffer.objects.filter(
            end_datetime__gt=now(), offer_type=ConditionalOffer.SITE)

    def get_active_vouchers(self):
        """
        Get all active vouchers. The returned ``Queryset`` of vouchers
        is filtered by end date greater then the current date.
        """
        return Voucher.objects.filter(end_datetime__gt=now())

    def get_number_of_promotions(self, abstract_base=AbstractPromotion):
        """
        Get the number of promotions for all promotions derived from
        *abstract_base*. All subclasses of *abstract_base* are queried
        and if another abstract base class is found this method is executed
        recursively.
        """
        total = 0
        for cls in abstract_base.__subclasses__():
            if cls._meta.abstract:
                total += self.get_number_of_promotions(cls)
            else:
                total += cls.objects.count()
        return total

    def get_open_baskets(self, filters=None):
        """
        Get all open baskets. If *filters* dictionary is provided they will
        be applied on all open baskets and return only filtered results.
        """
        if filters is None:
            filters = {}
        filters['status'] = Basket.OPEN
        return Basket.objects.filter(**filters)

    def get_hourly_report(self, hours=24, segments=10):
        """
        Get report of order revenue split up in hourly chunks. A report is
        generated for the last *hours* (default=24) from the current time.
        The report provides ``max_revenue`` of the hourly order revenue sum,
        ``y-range`` as the labeling for the y-axis in a template and
        ``order_total_hourly``, a list of properties for hourly chunks.
        *segments* defines the number of labeling segments used for the y-axis
        when generating the y-axis labels (default=10).
        """
        # Get datetime for 24 hours agao
        time_now = now().replace(minute=0, second=0)
        start_time = time_now - timedelta(hours=hours - 1)

        orders_last_day = Order.objects.filter(date_placed__gt=start_time)

        order_total_hourly = []
        for hour in range(0, hours, 2):
            end_time = start_time + timedelta(hours=2)
            hourly_orders = orders_last_day.filter(date_placed__gt=start_time,
                                                   date_placed__lt=end_time)
            total = hourly_orders.aggregate(
                Sum('total_incl_tax')
            )['total_incl_tax__sum'] or D('0.0')
            order_total_hourly.append({
                'end_time': end_time,
                'total_incl_tax': total
            })
            start_time = end_time

        max_value = max([x['total_incl_tax'] for x in order_total_hourly])
        divisor = 1
        while divisor < max_value / 50:
            divisor *= 10
        max_value = (max_value / divisor).quantize(D('1'), rounding=ROUND_UP)
        max_value *= divisor
        if max_value:
            segment_size = (max_value) / D('100.0')
            for item in order_total_hourly:
                item['percentage'] = int(item['total_incl_tax'] / segment_size)

            y_range = []
            y_axis_steps = max_value / D(str(segments))
            for idx in reversed(range(segments + 1)):
                y_range.append(idx * y_axis_steps)
        else:
            y_range = []
            for item in order_total_hourly:
                item['percentage'] = 0

        ctx = {
            'order_total_hourly': order_total_hourly,
            'max_revenue': max_value,
            'y_range': y_range,
        }
        return ctx

    def get_stats(self):
        datetime_24hrs_ago = now() - timedelta(hours=24)

        orders = Order.objects.all()
        orders_last_day = orders.filter(date_placed__gt=datetime_24hrs_ago)

        open_alerts = StockAlert.objects.filter(status=StockAlert.OPEN)
        closed_alerts = StockAlert.objects.filter(status=StockAlert.CLOSED)

        total_lines_last_day = Line.objects.filter(
            order__in=orders_last_day).count()
        stats = {
            'total_orders_last_day': orders_last_day.count(),
            'total_lines_last_day': total_lines_last_day,

            'average_order_costs': orders_last_day.aggregate(
                Avg('total_incl_tax')
            )['total_incl_tax__avg'] or D('0.00'),

            'total_revenue_last_day': orders_last_day.aggregate(
                Sum('total_incl_tax')
            )['total_incl_tax__sum'] or D('0.00'),

            'hourly_report_dict': self.get_hourly_report(hours=24),
            'total_customers_last_day': User.objects.filter(
                date_joined__gt=datetime_24hrs_ago,
            ).count(),

            'total_open_baskets_last_day': self.get_open_baskets({
                'date_created__gt': datetime_24hrs_ago
            }).count(),

            'total_products': Product.objects.count(),
            'total_open_stock_alerts': open_alerts.count(),
            'total_closed_stock_alerts': closed_alerts.count(),

            'total_site_offers': self.get_active_site_offers().count(),
            'total_vouchers': self.get_active_vouchers().count(),
            'total_promotions': self.get_number_of_promotions(),

            'total_customers': User.objects.count(),
            'total_open_baskets': self.get_open_baskets().count(),
            'total_orders': orders.count(),
            'total_lines': Line.objects.count(),
            'total_revenue': orders.aggregate(
                Sum('total_incl_tax')
            )['total_incl_tax__sum'] or D('0.00'),

            'order_status_breakdown': orders.order_by(
                'status'
            ).values('status').annotate(freq=Count('id'))
        }
        return stats

class IndexViewWithDate(TemplateView):
    """
    An overview view which displays several reports about the shop.

    Supports the permission-based dashboard. It is recommended to add a
    index_nonstaff.html template because Oscar's default template will
    display potentially sensitive store information.
    """

    def get_template_names(self):
        if self.request.user.is_staff:
            return ['dashboard/index.html', ]
        else:
            return ['dashboard/index_nonstaff.html', 'dashboard/index.html']

    def get_context_data(self, **kwargs):
        ctx = super(IndexViewWithDate, self).get_context_data(**kwargs)
        ctx.update(self.get_stats())

        year, month = int(datetime.now().year), int(datetime.now().month)
        cal = calendar.monthcalendar(year, month)
        dtstart = datetime(year, month, 1)
        last_day = max(cal[-1])
        dtend = datetime(year, month, last_day)
        cur_day = datetime(year, month, int(self.args[0]))
        day_num = int(self.args[0])

        # TODO Whether to include those occurrences that started in the previous
        # month but end in this month?
        subs = []
        subs_projects = []
        if self.request.user:
            subs = self.request.user.subscribeduser_set.all()

        for sub in subs:
            subs_projects.append(sub.project)

        queryset_project = None
        queryset_project = queryset_project._clone() if queryset_project is not None else Project.objects.select_related()
        start_projects = queryset_project.filter(start_date__year=year, start_date__month=month)
        end_projects = queryset_project.filter(end_date__year=year, end_date__month=month)

        projects_start = set(start_projects) & set(subs_projects)
        projects_end = set(end_projects) & set(subs_projects)

        def start_pj_day(o):
            return o.start_date.day

        def end_pj_day(o):
            return o.end_date.day

        def start_task_day(o):
            return o.expected_start_date.day

        def end_task_day(o):
            return o.expected_end_date.day

        tasks_start = []
        tasks_end = []
        all_tasks = []
        for project in subs_projects:
            all_tasks += project.new_tasks()

        start_projects_day = dict([(dt, list(o)) for dt, o in itertools.groupby(projects_start, start_pj_day)])
        end_projects_day = dict([(dt, list(o)) for dt, o in itertools.groupby(projects_end, end_pj_day)])
        start_tasks_day = dict([(dt, list(o)) for dt, o in itertools.groupby(all_tasks, start_task_day)])
        end_tasks_day = dict([(dt, list(o)) for dt, o in itertools.groupby(all_tasks, end_task_day)])


        ctx['calendar'] = [[(d, start_projects_day.get(d, []), end_projects_day.get(d, []), start_tasks_day.get(d, []), end_tasks_day.get(d, [])) for d in row] for row in cal]
        ctx['today'] = datetime.now()
        ctx['today_events'] = [(cur_day, start_projects_day.get(day_num, []), end_projects_day.get(day_num, []), start_tasks_day.get(day_num, []), end_tasks_day.get(day_num, []))]
        ctx['this_month'] = dtstart
        ctx['next_month'] = dtstart + timedelta(days=+last_day)
        ctx['last_month'] = dtstart + timedelta(days=-1)
        ctx['last_year'] = (year - 1)
        ctx['next_year'] = (year + 1)

        ctx['user_group'] = True
        is_investor = self.request.user.has_perm('investor.dashboard_access')
        is_company = self.request.user.has_perm('company.dashboard_access')
        is_partner = self.request.user.has_perm('partner.dashboard_access')
        if is_investor:
            ctx['group_type'] = 1
            ctx['current_user'] = self.request.user
            my_investor = []
            investors = Investor.objects.all()
            for investor in investors:
                if (self.request.user in investor.users.all()):
                    my_investor.append(investor)
            ctx['investor'] = my_investor[0]
            ctx['prospectuses'] = CompanyProspectus.objects.filter(status='Active')
        elif is_company:
            ctx['group_type'] = 2
            ctx['current_user'] = self.request.user
            my_companys = []
            companys = Company.objects.all()
            for company in companys:
                if (self.request.user in company.users.all()):
                    my_companys.append(company)
            ctx['company'] = my_companys[0]
        elif is_partner:
            ctx['group_type'] = 3
            ctx['current_user'] = self.request.user
            my_partners = []
            partners = Partner.objects.all()
            for partner in partners:
                if (self.request.user in partner.users.all()):
                    my_partners.append(partner)
            ctx['partner'] = my_partners[0]
        else:
            ctx['user_group'] = False
        return ctx

    def get_active_site_offers(self):
        """
        Return active conditional offers of type "site offer". The returned
        ``Queryset`` of site offers is filtered by end date greater then
        the current date.
        """
        return ConditionalOffer.objects.filter(
            end_datetime__gt=now(), offer_type=ConditionalOffer.SITE)

    def get_active_vouchers(self):
        """
        Get all active vouchers. The returned ``Queryset`` of vouchers
        is filtered by end date greater then the current date.
        """
        return Voucher.objects.filter(end_datetime__gt=now())

    def get_number_of_promotions(self, abstract_base=AbstractPromotion):
        """
        Get the number of promotions for all promotions derived from
        *abstract_base*. All subclasses of *abstract_base* are queried
        and if another abstract base class is found this method is executed
        recursively.
        """
        total = 0
        for cls in abstract_base.__subclasses__():
            if cls._meta.abstract:
                total += self.get_number_of_promotions(cls)
            else:
                total += cls.objects.count()
        return total

    def get_open_baskets(self, filters=None):
        """
        Get all open baskets. If *filters* dictionary is provided they will
        be applied on all open baskets and return only filtered results.
        """
        if filters is None:
            filters = {}
        filters['status'] = Basket.OPEN
        return Basket.objects.filter(**filters)

    def get_hourly_report(self, hours=24, segments=10):
        """
        Get report of order revenue split up in hourly chunks. A report is
        generated for the last *hours* (default=24) from the current time.
        The report provides ``max_revenue`` of the hourly order revenue sum,
        ``y-range`` as the labeling for the y-axis in a template and
        ``order_total_hourly``, a list of properties for hourly chunks.
        *segments* defines the number of labeling segments used for the y-axis
        when generating the y-axis labels (default=10).
        """
        # Get datetime for 24 hours agao
        time_now = now().replace(minute=0, second=0)
        start_time = time_now - timedelta(hours=hours - 1)

        orders_last_day = Order.objects.filter(date_placed__gt=start_time)

        order_total_hourly = []
        for hour in range(0, hours, 2):
            end_time = start_time + timedelta(hours=2)
            hourly_orders = orders_last_day.filter(date_placed__gt=start_time,
                                                   date_placed__lt=end_time)
            total = hourly_orders.aggregate(
                Sum('total_incl_tax')
            )['total_incl_tax__sum'] or D('0.0')
            order_total_hourly.append({
                'end_time': end_time,
                'total_incl_tax': total
            })
            start_time = end_time

        max_value = max([x['total_incl_tax'] for x in order_total_hourly])
        divisor = 1
        while divisor < max_value / 50:
            divisor *= 10
        max_value = (max_value / divisor).quantize(D('1'), rounding=ROUND_UP)
        max_value *= divisor
        if max_value:
            segment_size = (max_value) / D('100.0')
            for item in order_total_hourly:
                item['percentage'] = int(item['total_incl_tax'] / segment_size)

            y_range = []
            y_axis_steps = max_value / D(str(segments))
            for idx in reversed(range(segments + 1)):
                y_range.append(idx * y_axis_steps)
        else:
            y_range = []
            for item in order_total_hourly:
                item['percentage'] = 0

        ctx = {
            'order_total_hourly': order_total_hourly,
            'max_revenue': max_value,
            'y_range': y_range,
        }
        return ctx

    def get_stats(self):
        datetime_24hrs_ago = now() - timedelta(hours=24)

        orders = Order.objects.all()
        orders_last_day = orders.filter(date_placed__gt=datetime_24hrs_ago)

        open_alerts = StockAlert.objects.filter(status=StockAlert.OPEN)
        closed_alerts = StockAlert.objects.filter(status=StockAlert.CLOSED)

        total_lines_last_day = Line.objects.filter(
            order__in=orders_last_day).count()
        stats = {
            'total_orders_last_day': orders_last_day.count(),
            'total_lines_last_day': total_lines_last_day,

            'average_order_costs': orders_last_day.aggregate(
                Avg('total_incl_tax')
            )['total_incl_tax__avg'] or D('0.00'),

            'total_revenue_last_day': orders_last_day.aggregate(
                Sum('total_incl_tax')
            )['total_incl_tax__sum'] or D('0.00'),

            'hourly_report_dict': self.get_hourly_report(hours=24),
            'total_customers_last_day': User.objects.filter(
                date_joined__gt=datetime_24hrs_ago,
            ).count(),

            'total_open_baskets_last_day': self.get_open_baskets({
                'date_created__gt': datetime_24hrs_ago
            }).count(),

            'total_products': Product.objects.count(),
            'total_open_stock_alerts': open_alerts.count(),
            'total_closed_stock_alerts': closed_alerts.count(),

            'total_site_offers': self.get_active_site_offers().count(),
            'total_vouchers': self.get_active_vouchers().count(),
            'total_promotions': self.get_number_of_promotions(),

            'total_customers': User.objects.count(),
            'total_open_baskets': self.get_open_baskets().count(),
            'total_orders': orders.count(),
            'total_lines': Line.objects.count(),
            'total_revenue': orders.aggregate(
                Sum('total_incl_tax')
            )['total_incl_tax__sum'] or D('0.00'),

            'order_status_breakdown': orders.order_by(
                'status'
            ).values('status').annotate(freq=Count('id'))
        }
        return stats

class EventsIndexView(TemplateView):
    """
    An overview view which displays several reports about the shop.

    Supports the permission-based dashboard. It is recommended to add a
    index_nonstaff.html template because Oscar's default template will
    display potentially sensitive store information.
    """

    def get_template_names(self):
        if self.request.user.is_staff:
            return ['dashboard/events_index.html', ]
        else:
            return ['dashboard/index_nonstaff.html', 'dashboard/events_index.html']

    def get_context_data(self, **kwargs):
        ctx = super(EventsIndexView, self).get_context_data(**kwargs)
        ctx.update(self.get_stats())

        year, month = int(datetime.now().year), int(datetime.now().month)
        cal = calendar.monthcalendar(year, month)
        dtstart = datetime(year, month, 1)
        last_day = max(cal[-1])
        dtend = datetime(year, month, last_day)

        # TODO Whether to include those occurrences that started in the previous
        # month but end in this month?
        subs = []
        subs_projects = []
        if self.request.user:
            subs = self.request.user.subscribeduser_set.all()

        for sub in subs:
            subs_projects.append(sub.project)

        queryset_project = None
        queryset_project = queryset_project._clone() if queryset_project is not None else Project.objects.select_related()
        start_projects = queryset_project.filter(start_date__year=year, start_date__month=month)
        end_projects = queryset_project.filter(end_date__year=year, end_date__month=month)

        projects_start = set(start_projects) & set(subs_projects)
        projects_end = set(end_projects) & set(subs_projects)

        def start_pj_day(o):
            return o.start_date.day

        def end_pj_day(o):
            return o.end_date.day

        def start_task_day(o):
            return o.expected_start_date.day

        def end_task_day(o):
            return o.expected_end_date.day

        tasks_start = []
        tasks_end = []
        all_tasks = []
        for project in subs_projects:
            all_tasks += project.new_tasks()

        start_projects_day = dict([(dt, list(o)) for dt, o in itertools.groupby(projects_start, start_pj_day)])
        end_projects_day = dict([(dt, list(o)) for dt, o in itertools.groupby(projects_end, end_pj_day)])
        start_tasks_day = dict([(dt, list(o)) for dt, o in itertools.groupby(all_tasks, start_task_day)])
        end_tasks_day = dict([(dt, list(o)) for dt, o in itertools.groupby(all_tasks, end_task_day)])
        all_events = Event.objects.filter(user=self.request.user)
        queryset = None
        queryset = queryset._clone() if queryset is not None else Occurrence.objects.select_related()
        occurrences = queryset.filter(start_time__year=year, start_time__month=month, event__in=all_events)

        def start_event_day(o):
            return o.start_time.day

        events_day = dict([(dt, list(o)) for dt, o in itertools.groupby(occurrences, start_event_day)])

        ctx['calendar'] = [[(d, start_projects_day.get(d, []), end_projects_day.get(d, []), start_tasks_day.get(d, []), end_tasks_day.get(d, []), events_day.get(d, [])) for d in row] for row in cal]
        ctx['today'] = datetime.now()
        ctx['this_month'] = dtstart
        ctx['next_month'] = dtstart + timedelta(days=+last_day)
        ctx['last_month'] = dtstart + timedelta(days=-1)
        ctx['last_year'] = (year - 1)
        ctx['next_year'] = (year + 1)
        return ctx

    def get_active_site_offers(self):
        """
        Return active conditional offers of type "site offer". The returned
        ``Queryset`` of site offers is filtered by end date greater then
        the current date.
        """
        return ConditionalOffer.objects.filter(
            end_datetime__gt=now(), offer_type=ConditionalOffer.SITE)

    def get_active_vouchers(self):
        """
        Get all active vouchers. The returned ``Queryset`` of vouchers
        is filtered by end date greater then the current date.
        """
        return Voucher.objects.filter(end_datetime__gt=now())

    def get_number_of_promotions(self, abstract_base=AbstractPromotion):
        """
        Get the number of promotions for all promotions derived from
        *abstract_base*. All subclasses of *abstract_base* are queried
        and if another abstract base class is found this method is executed
        recursively.
        """
        total = 0
        for cls in abstract_base.__subclasses__():
            if cls._meta.abstract:
                total += self.get_number_of_promotions(cls)
            else:
                total += cls.objects.count()
        return total

    def get_open_baskets(self, filters=None):
        """
        Get all open baskets. If *filters* dictionary is provided they will
        be applied on all open baskets and return only filtered results.
        """
        if filters is None:
            filters = {}
        filters['status'] = Basket.OPEN
        return Basket.objects.filter(**filters)

    def get_hourly_report(self, hours=24, segments=10):
        """
        Get report of order revenue split up in hourly chunks. A report is
        generated for the last *hours* (default=24) from the current time.
        The report provides ``max_revenue`` of the hourly order revenue sum,
        ``y-range`` as the labeling for the y-axis in a template and
        ``order_total_hourly``, a list of properties for hourly chunks.
        *segments* defines the number of labeling segments used for the y-axis
        when generating the y-axis labels (default=10).
        """
        # Get datetime for 24 hours agao
        time_now = now().replace(minute=0, second=0)
        start_time = time_now - timedelta(hours=hours - 1)

        orders_last_day = Order.objects.filter(date_placed__gt=start_time)

        order_total_hourly = []
        for hour in range(0, hours, 2):
            end_time = start_time + timedelta(hours=2)
            hourly_orders = orders_last_day.filter(date_placed__gt=start_time,
                                                   date_placed__lt=end_time)
            total = hourly_orders.aggregate(
                Sum('total_incl_tax')
            )['total_incl_tax__sum'] or D('0.0')
            order_total_hourly.append({
                'end_time': end_time,
                'total_incl_tax': total
            })
            start_time = end_time

        max_value = max([x['total_incl_tax'] for x in order_total_hourly])
        divisor = 1
        while divisor < max_value / 50:
            divisor *= 10
        max_value = (max_value / divisor).quantize(D('1'), rounding=ROUND_UP)
        max_value *= divisor
        if max_value:
            segment_size = (max_value) / D('100.0')
            for item in order_total_hourly:
                item['percentage'] = int(item['total_incl_tax'] / segment_size)

            y_range = []
            y_axis_steps = max_value / D(str(segments))
            for idx in reversed(range(segments + 1)):
                y_range.append(idx * y_axis_steps)
        else:
            y_range = []
            for item in order_total_hourly:
                item['percentage'] = 0

        ctx = {
            'order_total_hourly': order_total_hourly,
            'max_revenue': max_value,
            'y_range': y_range,
        }
        return ctx

    def get_stats(self):
        datetime_24hrs_ago = now() - timedelta(hours=24)

        orders = Order.objects.all()
        orders_last_day = orders.filter(date_placed__gt=datetime_24hrs_ago)

        open_alerts = StockAlert.objects.filter(status=StockAlert.OPEN)
        closed_alerts = StockAlert.objects.filter(status=StockAlert.CLOSED)

        total_lines_last_day = Line.objects.filter(
            order__in=orders_last_day).count()
        stats = {
            'total_orders_last_day': orders_last_day.count(),
            'total_lines_last_day': total_lines_last_day,

            'average_order_costs': orders_last_day.aggregate(
                Avg('total_incl_tax')
            )['total_incl_tax__avg'] or D('0.00'),

            'total_revenue_last_day': orders_last_day.aggregate(
                Sum('total_incl_tax')
            )['total_incl_tax__sum'] or D('0.00'),

            'hourly_report_dict': self.get_hourly_report(hours=24),
            'total_customers_last_day': User.objects.filter(
                date_joined__gt=datetime_24hrs_ago,
            ).count(),

            'total_open_baskets_last_day': self.get_open_baskets({
                'date_created__gt': datetime_24hrs_ago
            }).count(),

            'total_products': Product.objects.count(),
            'total_open_stock_alerts': open_alerts.count(),
            'total_closed_stock_alerts': closed_alerts.count(),

            'total_site_offers': self.get_active_site_offers().count(),
            'total_vouchers': self.get_active_vouchers().count(),
            'total_promotions': self.get_number_of_promotions(),

            'total_customers': User.objects.count(),
            'total_open_baskets': self.get_open_baskets().count(),
            'total_orders': orders.count(),
            'total_lines': Line.objects.count(),
            'total_revenue': orders.aggregate(
                Sum('total_incl_tax')
            )['total_incl_tax__sum'] or D('0.00'),

            'order_status_breakdown': orders.order_by(
                'status'
            ).values('status').annotate(freq=Count('id'))
        }
        return stats


def dashboard_month_view(
        request,
        year,
        month,
        template='dashboard/swingtime/index.html',
        queryset=None
):
    '''
    Render a tradional calendar grid view with temporal navigation variables.

    Context parameters:

    ``today``
        the current datetime.datetime value

    ``calendar``
        a list of rows containing (day, items) cells, where day is the day of
        the month integer and items is a (potentially empty) list of occurrence
        for the day

    ``this_month``
        a datetime.datetime representing the first day of the month

    ``next_month``
        this_month + 1 month

    ``last_month``
        this_month - 1 month

    '''
    if request.user.is_staff:
        template = ['dashboard/events_index.html', ]
    else:
        template = ['dashboard/index_nonstaff.html', 'dashboard/events_index.html']
    year, month = int(year), int(month)
    cal = calendar.monthcalendar(year, month)
    dtstart = datetime(year, month, 1)
    last_day = max(cal[-1])
    dtend = datetime(year, month, last_day)

    # TODO Whether to include those occurrences that started in the previous
    # month but end in this month?
    #queryset = queryset._clone() if queryset is not None else Occurrence.objects.select_related()
    #occurrences = queryset.filter(start_time__year=year, start_time__month=month)
    subs = []
    subs_projects = []
    if request.user:
        subs = request.user.subscribeduser_set.all()

    for sub in subs:
        subs_projects.append(sub.project)

    queryset_project = None
    queryset_project = queryset_project._clone() if queryset_project is not None else Project.objects.select_related()
    start_projects = queryset_project.filter(start_date__year=year, start_date__month=month)
    end_projects = queryset_project.filter(end_date__year=year, end_date__month=month)

    projects_start= set(start_projects) & set(subs_projects)
    projects_end= set(end_projects) & set(subs_projects)
    def start_pj_day(o):
        return o.start_date.day
    def end_pj_day(o):
        return o.end_date.day
    def start_task_day(o):
        return o.expected_start_date.day
    def end_task_day(o):
        return o.expected_end_date.day

    tasks_start = []
    tasks_end = []
    all_tasks = []
    for project in subs_projects:
        all_tasks += project.new_tasks()


    start_projects_day = dict([(dt, list(o)) for dt, o in itertools.groupby(projects_start, start_pj_day)])
    end_projects_day = dict([(dt, list(o)) for dt, o in itertools.groupby(projects_end, end_pj_day)])
    start_tasks_day = dict([(dt, list(o)) for dt, o in itertools.groupby(all_tasks, start_task_day)])
    end_tasks_day = dict([(dt, list(o)) for dt, o in itertools.groupby(all_tasks, end_task_day)])

    all_events = Event.objects.filter(user=request.user)
    queryset = queryset._clone() if queryset is not None else Occurrence.objects.select_related()
    occurrences = queryset.filter(start_time__year=year, start_time__month=month, event__in=all_events)


    def start_event_day(o):
        return o.start_time.day

    events_day = dict([(dt, list(o)) for dt, o in itertools.groupby(occurrences, start_event_day)])

    data = {
        'today': datetime.now(),
        'calendar': [[(d, start_projects_day.get(d, []), end_projects_day.get(d, []), start_tasks_day.get(d, []), end_tasks_day.get(d, []), events_day.get(d,[])) for d in row] for row in cal],
        'this_month': dtstart,
        'next_month': dtstart + timedelta(days=+last_day),
        'last_month': dtstart + timedelta(days=-1),
        'last_year': (year - 1),
        'next_year': (year + 1),
        #'events': events,
        #'event_types': event_types
    }

    return render(request, template, data)


def dashboard_year_view(request, year, template='swingtime/yearly_view.html', queryset=None):
    '''

    Context parameters:

    ``year``
        an integer value for the year in questin

    ``next_year``
        year + 1

    ``last_year``
        year - 1

    ``by_month``
        a sorted list of (month, occurrences) tuples where month is a
        datetime.datetime object for the first day of a month and occurrences
        is a (potentially empty) list of values for that month. Only months
        which have at least 1 occurrence is represented in the list

    '''
    if request.user.is_staff:
        template = ['dashboard/events_years.html', ]
    else:
        template = ['dashboard/index_nonstaff.html', 'dashboard/events_years.html']
    year = int(year)
    queryset = queryset._clone() if queryset is not None else Occurrence.objects.select_related()
    occurrences = queryset.filter(
        models.Q(start_time__year=year) |
        models.Q(end_time__year=year)
    )

    subs = []
    subs_projects = []
    if request.user:
        subs = request.user.subscribeduser_set.all()

    for sub in subs:
        subs_projects.append(sub.project)

    queryset_project = None
    queryset_project = queryset_project._clone() if queryset_project is not None else Project.objects.select_related()
    yearly_projects = queryset_project.filter(
        models.Q(start_date__year=year) |
        models.Q(end_date__year=year)
    )

    projects = set(yearly_projects) & set(subs_projects)
    def group_key(o):
        return datetime(
            year,
            o.start_time.month if o.start_time.year == year else o.end_time.month,
            1
        )

    def group_project_key(o):
        return datetime(
            year,
            o.start_date.month if o.start_date.year == year else o.end_date.month,
            1
        )

    return render(request, template, {
        'year': year,
        'by_month': [(dt, list(o)) for dt, o in itertools.groupby(occurrences, group_key)],
        'by_month_project': [(dt, list(o)) for dt, o in itertools.groupby(projects, group_project_key)],
        'next_year': year + 1,
        'last_year': year - 1,
        'today': datetime.now()

    })


# -------------------------------------------------------------------------------
def _datetime_view(
        request,
        template,
        dt,
        timeslot_factory=None,
        items=None,
        params=None
):
    '''
    Build a time slot grid representation for the given datetime ``dt``. See
    utils.create_timeslot_table documentation for items and params.

    Context parameters:

    ``day``
        the specified datetime value (dt)

    ``next_day``
        day + 1 day

    ``prev_day``
        day - 1 day

    ``timeslots``
        time slot grid of (time, cells) rows

    '''
    timeslot_factory = timeslot_factory or utils.create_timeslot_table
    params = params or {}

    return render(request, template, {
        'today': datetime.now(),
        'day': dt,
        'next_day': dt + timedelta(days=+1),
        'prev_day': dt + timedelta(days=-1),
        'timeslots': timeslot_factory(dt, items, **params)
    })

# -------------------------------------------------------------------------------
def dashboard_day_view(request, year, month, day, template='swingtime/daily_view.html', **params):
    '''
    See documentation for function``_datetime_view``.

    '''
    if request.user.is_staff:
        template = ['dashboard/events_days.html', ]
    else:
        template = ['dashboard/index_nonstaff.html', 'dashboard/events_days.html']

    dt = datetime(int(year), int(month), int(day))
    return _datetime_view(request, template, dt, **params)


# -------------------------------------------------------------------------------
def dashboard_event_listing(
        request,
        template='swingtime/event_list.html',
        events=None,
        **extra_context
):
    '''
    View all ``events``.

    If ``events`` is a queryset, clone it. If ``None`` default to all ``Event``s.

    Context parameters:

    ``events``
        an iterable of ``Event`` objects

    ... plus all values passed in via **extra_context
    '''
    if request.user.is_staff:
        template = ['dashboard/event_list.html', ]
    else:
        template = ['dashboard/index_nonstaff.html', 'dashboard/event_list.html']

    if events is None:
        events = Event.objects.all()
    subs = []
    if request.user:
        subs = request.user.subscribeduser_set.all()

    extra_context['today'] = datetime.now()
    extra_context['events'] = events
    extra_context['subs'] = subs
    return render(request, template, extra_context)


from swingtime import utils as swingtime_utils
from oscar.apps.dashboard import forms as swingtime_forms
import logging
from django import http
from dateutil import parser
def add_event(
        request,
        template='dashboard/add_event.html',
        event_form_class=swingtime_forms.EventForm,
        recurrence_form_class=swingtime_forms.MultipleOccurrenceForm
):
    '''
    Add a new ``Event`` instance and 1 or more associated ``Occurrence``s.

    Context parameters:

    ``dtstart``
        a datetime.datetime object representing the GET request value if present,
        otherwise None

    ``event_form``
        a form object for updating the event

    ``recurrence_form``
        a form object for adding occurrences

    '''
    dtstart = None
    if request.method == 'POST':
        event_form = event_form_class(request.POST,initial={'request': request})
        recurrence_form = recurrence_form_class(request.POST)
        if event_form.is_valid() and recurrence_form.is_valid():
            event = event_form.save()
            recurrence_form.save(event)
            return http.HttpResponseRedirect(event.get_absolute_url())

    else:
        if 'dtstart' in request.GET:
            try:
                dtstart = parser.parse(request.GET['dtstart'])
            except(TypeError, ValueError) as exc:
                # TODO: A badly formatted date is passed to add_event
                logging.warning(exc)

        dtstart = dtstart or datetime.now()
        event_form = event_form_class(initial={'request': request})
        recurrence_form = recurrence_form_class(initial={'dtstart': dtstart})

    return render(
        request,
        template,
        {'dtstart': dtstart, 'event_form': event_form, 'recurrence_form': recurrence_form}
    )

def event_view(
        request,
        pk,
        template='dashboard/event_detail.html',
        event_form_class=swingtime_forms.EventForm,
        recurrence_form_class=swingtime_forms.MultipleOccurrenceForm
):
    '''
    View an ``Event`` instance and optionally update either the event or its
    occurrences.

    Context parameters:

    ``event``
        the event keyed by ``pk``

    ``event_form``
        a form object for updating the event

    ``recurrence_form``
        a form object for adding occurrences
    '''
    event = get_object_or_404(Event, pk=pk)
    event_form = recurrence_form = None
    if request.method == 'POST':
        if '_update' in request.POST:
            event_form = event_form_class(request.POST, instance=event)
            if event_form.is_valid():
                event_form.save(event)
                return http.HttpResponseRedirect(request.path)
        elif '_add' in request.POST:
            recurrence_form = recurrence_form_class(request.POST)
            if recurrence_form.is_valid():
                recurrence_form.save(event)
                return http.HttpResponseRedirect(request.path)
        else:
            return http.HttpResponseBadRequest('Bad Request')

    data = {
        'event': event,
        'event_form': event_form or event_form_class(instance=event),
        'recurrence_form': recurrence_form or recurrence_form_class(initial={'dtstart': datetime.now()})
    }
    return render(request, template, data)


def occurrence_view(
        request,
        event_pk,
        pk,
        template='dashboard/occurrence_detail.html',
        form_class=swingtime_forms.SingleOccurrenceForm
):
    '''
    View a specific occurrence and optionally handle any updates.

    Context parameters:

    ``occurrence``
        the occurrence object keyed by ``pk``

    ``form``
        a form object for updating the occurrence
    '''
    occurrence = get_object_or_404(Occurrence, pk=pk, event__pk=event_pk)
    if request.method == 'POST':
        form = form_class(request.POST, instance=occurrence)
        if form.is_valid():
            form.save()
            return http.HttpResponseRedirect(request.path)
    else:
        form = form_class(instance=occurrence)

    return render(request, template, {'occurrence': occurrence, 'form': form})