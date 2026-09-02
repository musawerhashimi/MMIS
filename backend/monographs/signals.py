"""
Side effects of monograph changes that must happen no matter which code path
caused them.

Kept narrow on purpose: anything a user explicitly does belongs in a service
where it is easy to follow. Signals here only maintain consistency that would
otherwise be easy to forget.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from monographs.models import Monograph, StageTransition


@receiver(post_save, sender=Monograph)
def record_initial_stage(sender, instance, created, **kwargs):
    """
    Give every monograph a first history row.

    Without this the timeline would start at the second stage and a student's
    own creation of the record would be invisible.
    """
    if not created:
        return
    StageTransition.objects.create(
        monograph=instance,
        from_stage="",
        to_stage=instance.stage,
        actor=instance.created_by,
        note="Monograph created.",
        created_by=instance.created_by,
    )


@receiver(post_save, sender=Monograph)
def stamp_supervisor_assignment(sender, instance, created, **kwargs):
    """
    Keep supervisor_assigned_at honest.

    The date a supervisor took the student on is used in workload reports, so
    it is set here rather than trusting every caller to remember it.
    """
    if instance.supervisor_id and instance.supervisor_assigned_at is None:
        Monograph.objects.filter(pk=instance.pk).update(
            supervisor_assigned_at=timezone.now()
        )
