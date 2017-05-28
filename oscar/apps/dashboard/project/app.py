from django.conf.urls import url

from oscar.core.application import DashboardApplication
from oscar.core.loading import get_class
from views import *
from rss import *
from task import *
from foo import *
from tasks import *
from wiki import *
from metrics import *
import pcalendar
import files

feeds = {
    'project': ProjectRss,
}

class ProjectDashboardApplication(DashboardApplication):
    name = None
    default_permissions = ['is_staff',]

    permissions_map = {
        'project-index' : (['is_staff'], ['partner.dashboard_access'], ['customer.dashboard_access']),
        'projects-index' : (['is_staff'], ['partner.dashboard_access'], ['customer.dashboard_access']),
        'project_details': (['is_staff'], ['partner.dashboard_access'], ['customer.dashboard_access']),
        'task_details': (['is_staff'], ['partner.dashboard_access'], ['customer.dashboard_access']),
        'edit_task': (['is_staff'], ['partner.dashboard_access'], ['customer.dashboard_access']),
        'task-order-select': (['is_staff'], ['partner.dashboard_access'], ['customer.dashboard_access']),
        'task-order-link': (['is_staff'], ['partner.dashboard_access'], ['customer.dashboard_access']),
        'task-order-unlink': (['is_staff'], ['partner.dashboard_access'], ['customer.dashboard_access']),
    }

    def get_urls(self):
        urls = [
            url(r'^projson/(?P<project_name>\w+)/$', proj_json),
            url(r'^json/(?P<project_name>\w+)/task/show/(?P<task_id>\d+)/$', show_task),
            url(r'^feeds2/(?P<url>.*)/$', proj_feed, {'feed_dict': feeds}),
            url(r'^$', index),
            url(r'^dashboard/$', dashboard, name='project-index'),
            url(r'^mainpage/$', ProjectMainPageView.as_view(), name='projects-index'),
            url(r'^(?P<project_name>\w+)/$', project_details, name='project_details'),
            url(r'^(?P<project_name>\w+)/settings/$', settings),
            url(r'^(?P<project_name>\w+)/logs/$', full_logs),
            url(r'^(?P<project_name>\w+)/noticeboard/$', noticeboard),
            url(r'^(?P<project_name>\w+)/todo/$', todo),
            url(r'^(?P<project_name>\w+)/tasks/$', project_tasks),
            url(r'^(?P<project_name>\w+)/taskhier/$', task_hierachy),
            url(r'^(?P<project_name>\w+)/tasks/quickentry/$', tasks_quickentry),
            url(r'^(?P<project_name>\w+)/taskitems/quickentry/$', taskitems_quickentry),
            url(r'^(?P<project_name>\w+)/taskdetails/(?P<task_num>\d+)/$', task_details, name='task_details'),
            url(r'^(?P<project_name>\w+)/taskorderselection/(?P<task_num>\d+)/$', task_order_selection, name='task-order-select'),
            url(r'^task/(?P<task_pk>\d+)/order/(?P<order_pk>\d+)/link/$', TaskOrderLinkView.as_view(), name='task-order-link'),
            url(r'^task/(?P<task_pk>\d+)/order/(?P<order_pk>\d+)/unlink/$', TaskOrderUnLinkView.as_view(),
                name='task-order-unlink'),
            url(r'^(?P<project_name>\w+)/taskhistory/(?P<task_num>\d+)/$', task_history),
            url(r'^(?P<project_name>\w+)/taskdetails/(?P<task_num>\d+)/addnote/$', add_task_note),
            url(r'^(?P<project_name>\w+)/edittask/(?P<task_num>\d+)/$', edit_task, name = 'edit_task'),
            url(r'^(?P<project_name>\w+)/taskrevision/(?P<task_id>\d+)/$', task_revision),
            url(r'^(?P<project_name>\w+)/edititem/(?P<taskitem_num>\d+)/$', edit_task_item),
            url(r'^(?P<project_name>\w+)/taskitemhistory/(?P<taskitem_num>\d+)/$', taskitem_history),
            url(r'^(?P<project_name>\w+)/itemrevision/(?P<taskitem_id>\d+)/$', taskitem_revision),
            url(r'^(?P<project_name>\w+)/taskitemhist/(?P<taskitem_num>\d+)/$', taskitem_history),
            url(r'^(?P<project_name>\w+)/wiki/$', wiki),
            url(r'^(?P<project_name>\w+)/wiki/new/$', create_wikipage),
            url(r'^(?P<project_name>\w+)/wiki/(?P<page_name>\w+)/$', wikipage),
            url(r'^(?P<project_name>\w+)/wiki/(?P<page_name>\w+)/revisions/$', wikipage_diff),
            url(r'^(?P<project_name>\w+)/wiki/(?P<page_name>\w+)/edit/$', edit_wikipage),
            url(r'^(?P<project_name>\w+)/wiki/(?P<page_name>\w+)/revisions/(?P<revision_id>\d+)/$', wiki_revision),
            url(r'^(?P<project_name>\w+)/health/$', project_health),
            url(r'^(?P<project_name>\w+)/userstats/$', user_stats),
            #url(r'^(?P<project_name>\w+)/files/$', files),
            url(r'^(?P<project_name>\w+)/calendar/$', pcalendar.index),
            url(r'^(?P<project_name>\w+)/calendar/(?P<year>\d+)/(?P<month>\d+)/$', pcalendar.month_cal),
        ]
        return self.post_process_urls(urls)


application = ProjectDashboardApplication()
