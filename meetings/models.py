from django.db import models


class Meeting(models.Model):

    title = models.CharField(
        max_length=200
    )

    transcript = models.TextField(
        blank=True,
        default=""
    )

    summary = models.TextField(
        blank=True,
        default=""
    )

    decisions = models.TextField(
        blank=True,
        default=""
    )

    action_items = models.TextField(
        blank=True,
        default=""
    )

    deadlines = models.TextField(
        blank=True,
        default=""
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.title