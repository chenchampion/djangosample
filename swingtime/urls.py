from django.conf.urls import url
from swingtime import views

urlpatterns = [
    url(
        r'^(?:calendar/)?$', 
        views.today_view, 
        name='swingtime-today'
    ),

    url(
        r'^calendar/(?P<year>\d{4})/$', 
        views.year_view, 
        name='swingtime-yearly-view'
    ),

    url(
        r'^calendar/(\d{4})/(0?[1-9]|1[012])/$', 
        views.month_view, 
        name='swingtime-monthly-view'
    ),

    url(
        r'^calendar/(\d{4})/(0?[1-9]|1[012])/([0-3]?\d)/$', 
        views.day_view, 
        name='swingtime-daily-view'
    ),

    url(
        r'^events/$',
        views.event_listing,
        name='swingtime-events'
    ),
        
    url(
        r'^events/add/$', 
        views.add_event, 
        name='swingtime-add-event'
    ),
    
    url(
        r'^events/(\d+)/$', 
        views.event_view, 
        name='swingtime-event'
    ),
    
    url(
        r'^events/(\d+)/(\d+)/$', 
        views.occurrence_view, 
        name='swingtime-occurrence'
    ),

    url(
        r'^events/add_event_type$',
        views.add_event_tpye,
        name='add-events-type'
    ),

    url(
        r'^events/list_event_types$',
        views.list_event_types,
        name='list-event-types'
    ),
    url(
        r'^events/event_type_detail/(?P<slug>[-\w]+)/$',
        views.event_type_detail,
        name='event-types-detail'
    ),

    url(
        r'^events/event_listing_for_event_type/(?P<eventtype>[-\w]+)/$',
        views.event_listing_for_event_type,
        name='event_listing_for_event_type'
    ),
]