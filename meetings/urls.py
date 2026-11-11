from django.urls import path

from . import views


urlpatterns = [
    path(
        "",
        views.meeting_list,
        name="meeting_list"
    ),

    path(
        "meeting/new/",
        views.create_meeting,
        name="create_meeting"
    ),

    path(
        "meeting/<int:meeting_id>/",
        views.meeting_room,
        name="meeting_room"
    ),

    path(
        "meeting/<int:meeting_id>/report/",
        views.meeting_report,
        name="meeting_report"
    ),
]