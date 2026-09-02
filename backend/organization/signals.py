"""
Consistency the application must never be able to forget.

A department without rules cannot approve a topic, size a committee or work
out a grade. Creating one was handled in three separate places and missed in
a fourth — the admin — so a department added there had no policy at all.
Doing it here means no code path can skip it.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from organization.models import Department, DepartmentPolicy


@receiver(post_save, sender=Department)
def give_every_department_its_rules(sender, instance, created, **kwargs):
    """
    Attach a policy the moment a department exists.

    The defaults are a starting point, not an answer: a head of department
    is expected to confirm them before anyone uses the system.
    """
    if created:
        DepartmentPolicy.objects.get_or_create(department=instance)
