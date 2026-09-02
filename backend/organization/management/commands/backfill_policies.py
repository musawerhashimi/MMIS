"""
Give rules to any department that has none.

Departments created before policies were guaranteed at the model level may
have none, and a department without rules cannot approve a topic, size a
committee or work out a grade. Safe to run at any time: it only fills gaps.
"""
from django.core.management.base import BaseCommand

from organization.models import Department, DepartmentPolicy


class Command(BaseCommand):
    help = "Create a default policy for any department missing one."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what is missing without changing anything.",
        )

    def handle(self, *args, **options):
        missing = [
            department
            for department in Department.objects.all()
            if not DepartmentPolicy.objects.filter(department=department).exists()
        ]

        if not missing:
            self.stdout.write(self.style.SUCCESS("Every department already has rules."))
            return

        for department in missing:
            if options["dry_run"]:
                self.stdout.write(f"  would add rules to {department.name}")
                continue
            DepartmentPolicy.objects.create(department=department)
            self.stdout.write(f"  rules added to {department.name}")

        if options["dry_run"]:
            self.stdout.write(f"\n{len(missing)} department(s) need attention.")
            return

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"{len(missing)} department(s) fixed. Ask the head of each to confirm "
            f"the defaults before anyone uses the system."
        ))
