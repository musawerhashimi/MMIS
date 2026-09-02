"""Account administration."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from accounts.models import StudentProfile, SupervisorProfile, User


class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    extra = 0


class SupervisorProfileInline(admin.StackedInline):
    model = SupervisorProfile
    can_delete = False
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    People, keyed by university ID rather than email.

    The profile inlines shown depend on the role, so a student row is not
    cluttered with supervisor fields and the other way round.
    """

    form = UserChangeForm
    add_form = UserCreationForm

    list_display = ("username", "full_name", "role", "department", "is_active", "last_seen_at")
    list_filter = ("role", "is_active", "department")
    search_fields = ("username", "full_name", "email")
    ordering = ("full_name",)
    readonly_fields = ("id", "last_seen_at", "created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal", {"fields": ("full_name", "title", "email", "phone", "avatar")}),
        ("Role", {"fields": ("role", "department")}),
        ("Access", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Record", {"fields": ("id", "last_seen_at", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "full_name", "role", "department", "password1", "password2"),
        }),
    )

    def get_inlines(self, request, obj=None):
        if obj is None:
            return []
        if obj.is_student:
            return [StudentProfileInline]
        if obj.can_supervise:
            return [SupervisorProfileInline]
        return []


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("student_id", "user", "program", "enrollment_year")
    search_fields = ("student_id", "user__full_name")


@admin.register(SupervisorProfile)
class SupervisorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "specialization", "active_student_count", "effective_max_students",
                    "is_accepting_students")
    search_fields = ("user__full_name", "specialization")

    @admin.display(description="Active students")
    def active_student_count(self, obj):
        return obj.active_student_count

    @admin.display(description="Limit")
    def effective_max_students(self, obj):
        return obj.effective_max_students
