"""
Role-based permission classes.

Access in this system is rarely "can this role touch this endpoint" — it is
almost always "does this person stand in the right relationship to *this
monograph*". The object-level classes below encode those relationships once
so views stay thin.
"""
from rest_framework import permissions

from core.enums import Role


class IsAdmin(permissions.BasePermission):
    message = "Only an administrator can do this."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin)


class IsHeadOfDepartment(permissions.BasePermission):
    message = "Only the head of department can do this."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.is_head_of_department or u.is_admin))


class IsSupervisor(permissions.BasePermission):
    message = "Only a supervisor can do this."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.is_supervisor or u.is_admin))


class IsStudent(permissions.BasePermission):
    message = "Only a student can do this."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_student)


class IsStaff(permissions.BasePermission):
    """Any non-student role: supervisor, head, committee member or admin."""

    message = "Only staff can do this."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and not u.is_student)


class HasRole(permissions.BasePermission):
    """
    Declarative role check.

        class MyView(APIView):
            permission_classes = [HasRole.of(Role.HOD, Role.ADMIN)]
    """

    allowed_roles: tuple = ()
    message = "Your role does not allow this action."

    @classmethod
    def of(cls, *roles):
        return type("HasRoleChecked", (cls,), {"allowed_roles": tuple(roles)})

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        return u.role in self.allowed_roles or u.role == Role.ADMIN


class IsMonographParticipant(permissions.BasePermission):
    """
    Read access to a monograph.

    Granted to its student authors, its supervisor, the head of the owning
    department, anyone on its defense committee, and administrators.
    """

    message = "You are not involved in this monograph."

    def has_object_permission(self, request, view, obj):
        monograph = getattr(obj, "monograph", obj)
        return monograph.is_visible_to(request.user)


class CanEditMonograph(permissions.BasePermission):
    """
    Write access to the monograph record itself.

    Students may only edit while the topic is still theirs to change; once it
    is submitted the record is locked and only staff can move it.
    """

    message = "You cannot change this monograph at its current stage."

    def has_object_permission(self, request, view, obj):
        monograph = getattr(obj, "monograph", obj)
        if request.method in permissions.SAFE_METHODS:
            return monograph.is_visible_to(request.user)
        return monograph.is_editable_by(request.user)


class ReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS
