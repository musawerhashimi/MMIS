"""
Housekeeping the university server does for itself.

There is no full-time sysadmin at the other end, so the system takes its own
backups: four years of student work must survive a failed hard disk.
"""
import logging
import shutil
import subprocess
from datetime import timedelta
from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

BACKUP_DIR = Path(getattr(settings, "BACKUP_ROOT", settings.BASE_DIR / "backups"))
KEEP_DAYS = getattr(settings, "BACKUP_KEEP_DAYS", 30)


@shared_task
def backup_database() -> dict:
    """
    Take a copy of the database.

    Runs nightly. Handles both the SQLite file used on small installations and
    Postgres on larger ones, because a department may start on one and move to
    the other.
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = timezone.now().strftime("%Y%m%d-%H%M")
    config = settings.DATABASES["default"]

    if "sqlite" in config["ENGINE"]:
        source = Path(config["NAME"])
        if not source.exists():
            return {"status": "skipped", "reason": "no database file"}
        target = BACKUP_DIR / f"db-{stamp}.sqlite3"
        # sqlite3's own backup API would be safer under load, but a file copy
        # is adequate for a nightly job on a single-department installation.
        shutil.copy2(source, target)
        size = target.stat().st_size

    else:
        target = BACKUP_DIR / f"db-{stamp}.sql"
        command = [
            "pg_dump",
            "-h", config.get("HOST", "localhost"),
            "-p", str(config.get("PORT", 5432)),
            "-U", config["USER"],
            "-d", config["NAME"],
            "-f", str(target),
        ]
        env = {"PGPASSWORD": config.get("PASSWORD", "")}
        try:
            subprocess.run(command, check=True, env=env, capture_output=True, timeout=600)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
            logger.exception("Database backup failed")
            return {"status": "failed", "error": str(exc)[:200]}
        size = target.stat().st_size if target.exists() else 0

    logger.info("Database backed up to %s (%s bytes)", target.name, size)
    return {"status": "ok", "file": target.name, "bytes": size}


@shared_task
def backup_documents() -> dict:
    """
    Archive the uploaded files.

    Student work is irreplaceable — a lost proposal cannot be regenerated from
    the database — so the files are copied alongside the data.
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    source = Path(settings.PRIVATE_MEDIA_ROOT)
    if not source.exists() or not any(source.iterdir()):
        return {"status": "skipped", "reason": "no documents yet"}

    stamp = timezone.now().strftime("%Y%m%d-%H%M")
    target = BACKUP_DIR / f"documents-{stamp}"
    archive = shutil.make_archive(str(target), "gztar", root_dir=str(source))
    size = Path(archive).stat().st_size

    logger.info("Documents archived to %s (%s bytes)", Path(archive).name, size)
    return {"status": "ok", "file": Path(archive).name, "bytes": size}


@shared_task
def prune_old_backups(keep_days: int | None = None) -> dict:
    """
    Delete backups older than the retention window.

    Without this the disk fills quietly and the next backup fails on a machine
    nobody is watching.
    """
    keep = keep_days or KEEP_DAYS
    if not BACKUP_DIR.exists():
        return {"status": "skipped", "removed": 0}

    cutoff = timezone.now() - timedelta(days=keep)
    removed = 0
    for path in BACKUP_DIR.iterdir():
        if not path.is_file():
            continue
        modified = timezone.datetime.fromtimestamp(
            path.stat().st_mtime, tz=timezone.get_current_timezone()
        )
        if modified < cutoff:
            path.unlink()
            removed += 1

    logger.info("Pruned %s old backup(s)", removed)
    return {"status": "ok", "removed": removed, "kept_days": keep}


@shared_task
def nightly_backup() -> dict:
    """The full nightly backup: data, files, then cleanup."""
    return {
        "database": backup_database(),
        "documents": backup_documents(),
        "pruned": prune_old_backups(),
    }
