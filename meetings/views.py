from django.shortcuts import get_object_or_404, redirect, render

from .models import Meeting


def meeting_list(request):
    """
    Display all meetings, newest first.
    """

    meetings = Meeting.objects.all().order_by("-created_at")

    return render(
        request,
        "meetings/meeting_list.html",
        {
            "meetings": meetings
        }
    )


def create_meeting(request):
    """
    Create a new meeting and open its meeting room.
    """

    if request.method == "POST":

        meeting = Meeting.objects.create(
            title="New Meeting"
        )

        return redirect(
            "meeting_room",
            meeting_id=meeting.id
        )

    return redirect("meeting_list")


def meeting_room(request, meeting_id):
    """
    Open the live meeting room.
    """

    meeting = get_object_or_404(
        Meeting,
        id=meeting_id
    )

    return render(
        request,
        "meetings/meeting_room.html",
        {
            "meeting": meeting
        }
    )


def meeting_report(request, meeting_id):
    """
    Display the completed meeting report.
    """

    meeting = get_object_or_404(
        Meeting,
        id=meeting_id
    )

    return render(
        request,
        "meetings/meeting_report.html",
        {
            "meeting": meeting
        }
    )