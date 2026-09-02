"""Authentication and user management endpoints."""
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from accounts.models import User
from accounts.serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    MeSerializer,
    UserCreateSerializer,
    UserSerializer,
)
from core.enums import Role
from core.permissions import IsAdmin


class LoginView(TokenObtainPairView):
    """Sign in with a university ID and password."""

    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            username = request.data.get("username")
            User.objects.filter(username=username).update(last_seen_at=timezone.now())
        return response


class MeView(APIView):
    """The signed-in person's own record."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(MeSerializer(request.user, context={"request": request}).data)

    def patch(self, request):
        # Only the fields a person may change about themselves.
        allowed = {"full_name", "email", "phone", "avatar", "title"}
        data = {k: v for k, v in request.data.items() if k in allowed}
        serializer = MeSerializer(
            request.user, data=data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Your password has been changed."})


class UserViewSet(viewsets.ModelViewSet):
    """
    Account administration.

    Listing is open to any signed-in user because supervisors and heads of
    department need to pick people when assigning work; creating and editing
    accounts is restricted to administrators.
    """

    queryset = User.objects.select_related("department").all()
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["role", "department", "is_active"]
    search_fields = ["full_name", "username", "email"]
    ordering_fields = ["full_name", "created_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve", "supervisors"):
            return [IsAuthenticated()]
        return [IsAdmin()]

    @action(detail=False, methods=["get"])
    def supervisors(self, request):
        """
        People who can take on students, with their current load.

        Used by the head of department when assigning a supervisor, which is
        why capacity travels with each row.
        """
        queryset = (
            User.objects.filter(
                role__in=[Role.SUPERVISOR, Role.HEAD_OF_DEPARTMENT], is_active=True
            )
            .select_related("supervisor_profile", "department")
        )
        department = request.query_params.get("department")
        if department:
            queryset = queryset.filter(department_id=department)

        payload = []
        for user in queryset:
            profile = getattr(user, "supervisor_profile", None)
            payload.append(
                {
                    "id": str(user.id),
                    "full_name": user.full_name,
                    "display_name": user.display_name,
                    "department": str(user.department_id) if user.department_id else None,
                    "specialization": profile.specialization if profile else "",
                    "active_students": profile.active_student_count if profile else 0,
                    "max_students": profile.effective_max_students if profile else None,
                    "has_capacity": profile.has_capacity if profile else True,
                }
            )
        return Response(payload)

    @action(detail=True, methods=["post"], permission_classes=[IsAdmin])
    def deactivate(self, request, pk=None):
        """
        Switch an account off rather than deleting it.

        Accounts are never removed: a graduated student's name must still
        appear on their archived monograph.
        """
        user = self.get_object()
        user.is_active = False
        user.save(update_fields=["is_active"])
        return Response({"detail": f"{user.full_name} can no longer sign in."})

    @action(detail=True, methods=["post"], permission_classes=[IsAdmin])
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=["is_active"])
        return Response({"detail": f"{user.full_name} can sign in again."})

    @action(detail=True, methods=["post"], permission_classes=[IsAdmin])
    def reset_password(self, request, pk=None):
        """
        Set a new password for someone who has forgotten theirs.

        Password recovery runs through the administrator because the system
        does not depend on students having working email.
        """
        user = self.get_object()
        new_password = request.data.get("new_password")
        if not new_password:
            return Response(
                {"error": {"code": "validation", "message": "A new password is required.",
                           "details": {"new_password": "This field is required."}}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(new_password)
        user.save(update_fields=["password"])
        return Response({"detail": f"Password reset for {user.full_name}."})
