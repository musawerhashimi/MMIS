"""
Users and roles.

Login is by university ID, not email: many students do not use email
regularly, so email is optional and never required to sign in or to receive
notifications.
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from core.enums import Role
from core.models import TimeStampedModel, UUIDModel


class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra):
        if not username:
            raise ValueError("A username (university ID) is required.")
        email = extra.pop("email", "") or ""
        user = self.model(
            username=username,
            email=self.normalize_email(email) if email else "",
            **extra,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra):
        extra.setdefault("role", Role.ADMIN)
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_active", True)

        if extra.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(username, password, **extra)


class User(AbstractBaseUser, PermissionsMixin, UUIDModel, TimeStampedModel):
    """
    One account per person.

    A person has exactly one primary role. A supervisor who also sits on
    defense committees is still a supervisor; committee membership is recorded
    per defense rather than as a second role, so roles stay simple.
    """

    # University ID (student number or staff number). This is what people type
    # to log in.
    username = models.CharField(max_length=64, unique=True, db_index=True)

    full_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        db_index=True,
    )

    department = models.ForeignKey(
        "organization.Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="members",
    )

    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)

    # Academic title shown on printed forms ("Prof.", "Dr.", "Eng.").
    title = models.CharField(max_length=32, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # Django admin access

    last_seen_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        ordering = ("full_name",)
        indexes = [
            models.Index(fields=["role", "department"]),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.username})"

    # -- Role helpers -----------------------------------------------------
    # Used constantly by permissions and serializers, so they live here
    # rather than being re-derived from the role string everywhere.

    @property
    def is_student(self) -> bool:
        return self.role == Role.STUDENT

    @property
    def is_supervisor(self) -> bool:
        return self.role == Role.SUPERVISOR

    @property
    def is_head_of_department(self) -> bool:
        return self.role == Role.HEAD_OF_DEPARTMENT

    @property
    def is_committee_member(self) -> bool:
        return self.role == Role.COMMITTEE_MEMBER

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN or self.is_superuser

    @property
    def can_supervise(self) -> bool:
        """Heads of department supervise students too."""
        return self.role in (Role.SUPERVISOR, Role.HEAD_OF_DEPARTMENT)

    @property
    def display_name(self) -> str:
        return f"{self.title} {self.full_name}".strip()

    def touch_last_seen(self):
        self.last_seen_at = timezone.now()
        self.save(update_fields=["last_seen_at"])


class StudentProfile(UUIDModel, TimeStampedModel):
    """
    Extra details that only apply to students.

    Kept separate from User so staff rows are not cluttered with empty
    academic fields.
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="student_profile"
    )
    student_id = models.CharField(max_length=64, unique=True, db_index=True)
    enrollment_year = models.PositiveIntegerField(null=True, blank=True)
    program = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("student_id",)

    def __str__(self):
        return f"{self.user.full_name} — {self.student_id}"


class SupervisorProfile(UUIDModel, TimeStampedModel):
    """
    Extra details for people who supervise.

    ``max_students`` is the workload cap. The department policy sets a default
    and this field overrides it for an individual, because a department head
    often carries fewer students than a full-time supervisor.
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="supervisor_profile"
    )
    specialization = models.CharField(max_length=255, blank=True)
    max_students = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Leave empty to use the department default.",
    )
    is_accepting_students = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.display_name}"

    @property
    def effective_max_students(self) -> int:
        if self.max_students is not None:
            return self.max_students
        dept = self.user.department
        if dept and hasattr(dept, "policy"):
            return dept.policy.default_max_students_per_supervisor
        return 10

    @property
    def active_student_count(self) -> int:
        """Students currently being supervised on unfinished monographs."""
        from core.enums import FINISHED_STAGES

        return self.user.supervised_monographs.exclude(stage__in=FINISHED_STAGES).count()

    @property
    def has_capacity(self) -> bool:
        return self.is_accepting_students and self.active_student_count < self.effective_max_students
