"""Authentication and user serializers."""
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from accounts.models import StudentProfile, SupervisorProfile, User


class StudentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = ("student_id", "enrollment_year", "program")


class SupervisorProfileSerializer(serializers.ModelSerializer):
    effective_max_students = serializers.IntegerField(read_only=True)
    active_student_count = serializers.IntegerField(read_only=True)
    has_capacity = serializers.BooleanField(read_only=True)

    class Meta:
        model = SupervisorProfile
        fields = (
            "specialization",
            "max_students",
            "is_accepting_students",
            "effective_max_students",
            "active_student_count",
            "has_capacity",
        )


class UserSerializer(serializers.ModelSerializer):
    """The full user record, used on profile screens and in admin lists."""

    display_name = serializers.CharField(read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    student_profile = StudentProfileSerializer(read_only=True)
    supervisor_profile = SupervisorProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "full_name",
            "display_name",
            "title",
            "email",
            "phone",
            "role",
            "department",
            "department_name",
            "avatar",
            "is_active",
            "last_seen_at",
            "created_at",
            "student_profile",
            "supervisor_profile",
        )
        read_only_fields = ("id", "role", "last_seen_at", "created_at")


class MeSerializer(UserSerializer):
    """
    What the signed-in person sees about themselves.

    Adds the capability flags the frontend uses to decide which navigation and
    actions to render, so the UI does not have to re-derive them from the role
    string.
    """

    permissions = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ("permissions",)

    def get_permissions(self, obj) -> dict:
        return {
            "is_student": obj.is_student,
            "is_supervisor": obj.is_supervisor,
            "is_head_of_department": obj.is_head_of_department,
            "is_committee_member": obj.is_committee_member,
            "is_admin": obj.is_admin,
            "can_supervise": obj.can_supervise,
        }


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Administrator-only account creation.

    Email is optional throughout: students log in with their university ID and
    receive notifications inside the system, so an account is fully usable
    without one.
    """

    password = serializers.CharField(write_only=True, validators=[validate_password])
    student_id = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "full_name",
            "title",
            "email",
            "phone",
            "role",
            "department",
            "password",
            "student_id",
        )

    def validate(self, attrs):
        from core.enums import Role

        if attrs.get("role") == Role.STUDENT and not attrs.get("student_id"):
            raise serializers.ValidationError(
                {"student_id": "A student ID is required for student accounts."}
            )
        return attrs

    def create(self, validated_data):
        from core.enums import Role

        student_id = validated_data.pop("student_id", "")
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)

        if user.role == Role.STUDENT:
            StudentProfile.objects.create(user=user, student_id=student_id)
        elif user.can_supervise:
            SupervisorProfile.objects.create(user=user)
        return user


class LoginSerializer(TokenObtainPairSerializer):
    """
    Login by university ID.

    The user record travels back with the tokens so the app can render the
    dashboard immediately rather than making a second request for it.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["full_name"] = user.full_name
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = MeSerializer(self.user, context=self.context).data
        return data


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Your current password is not correct.")
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user
