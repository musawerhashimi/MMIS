"""
Rebuild the printable handbook.

The handbook is written as HTML in docs/handbook-print.html and rendered to
PDF here, so the version staff are handed and the version in the repository
never drift apart.

    python manage.py build_handbook
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Render docs/handbook-print.html to docs/Monograph-System-Handbook.pdf"

    def handle(self, *args, **options):
        # WeasyPrint pulls in large native libraries, so it is imported only
        # when this command actually runs.
        from weasyprint import HTML

        docs = Path(settings.BASE_DIR).parent / "docs"
        source = docs / "handbook-print.html"
        target = docs / "Monograph-System-Handbook.pdf"

        if not source.exists():
            raise CommandError(f"Cannot find {source}")

        HTML(filename=str(source)).write_pdf(str(target))

        size = target.stat().st_size
        self.stdout.write(
            self.style.SUCCESS(f"Wrote {target.name} ({size:,} bytes)")
        )
