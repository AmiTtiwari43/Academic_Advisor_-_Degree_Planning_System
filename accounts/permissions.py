from django.contrib.auth.models import User
from rest_framework import permissions

from accounts.models import AdvisorAssignment, InstitutionMembership, Role
from institutions.models import Institution


# Unified RBAC Role Groupings: Moderator, Mentor, Student
MODERATOR_ROLES = [Role.COORDINATOR, Role.HOD, Role.ADMIN, Role.MODERATOR]
MENTOR_ROLES = [Role.ADVISOR, Role.MENTOR]
STUDENT_ROLES = [Role.STUDENT]


def get_user_roles_for_institution(user: User, institution: Institution) -> list[str]:
    """
    Returns active roles for a user within a specific institution.
    """
    if not user.is_authenticated:
        return []
    return list(
        InstitutionMembership.objects.filter(
            user=user,
            institution=institution,
            is_active=True,
        ).values_list("role", flat=True)
    )


def can_view_student_record(
    actor_user: User,
    student_user: User,
    institution: Institution,
) -> bool:
    """
    Determines if actor_user has permission to view student_user's academic record
    in the context of institution.
    """
    if not actor_user.is_authenticated or not actor_user.is_active:
        return False

    if actor_user.is_superuser:
        return True

    roles = get_user_roles_for_institution(actor_user, institution)
    if not roles:
        return False

    # Moderators (Coordinators, HODs, Admins) can view any student in their institution
    if any(r in roles for r in MODERATOR_ROLES):
        return True

    # Student viewing own record
    if actor_user.id == student_user.id:
        return any(r in roles for r in STUDENT_ROLES)

    # Faculty advisor / Mentor viewing assigned advisee
    if any(r in roles for r in MENTOR_ROLES):
        advisor_membership = InstitutionMembership.objects.filter(
            user=actor_user,
            institution=institution,
            role__in=MENTOR_ROLES,
            is_active=True,
        ).first()

        student_membership = InstitutionMembership.objects.filter(
            user=student_user,
            institution=institution,
            role__in=STUDENT_ROLES,
            is_active=True,
        ).first()

        if advisor_membership and student_membership:
            return AdvisorAssignment.objects.filter(
                institution=institution,
                advisor=advisor_membership,
                student=student_membership,
                is_active=True,
            ).exists()

    return False


def can_manage_curriculum(actor_user: User, institution: Institution) -> bool:
    """
    Determines if actor_user can build, edit, or publish curriculum for the given institution.
    """
    if not actor_user.is_authenticated or not actor_user.is_active:
        return False
    if actor_user.is_superuser:
        return True
    roles = get_user_roles_for_institution(actor_user, institution)
    return any(r in roles for r in MODERATOR_ROLES)


def can_assign_advisor(actor_user: User, institution: Institution) -> bool:
    """
    Determines if actor_user can assign advisors to students in the institution.
    """
    if not actor_user.is_authenticated or not actor_user.is_active:
        return False
    if actor_user.is_superuser:
        return True
    roles = get_user_roles_for_institution(actor_user, institution)
    return any(r in roles for r in MODERATOR_ROLES)


def can_manage_institution(actor_user: User, institution: Institution) -> bool:
    """
    Determines if actor_user has administrative privileges for the institution.
    """
    if not actor_user.is_authenticated or not actor_user.is_active:
        return False
    if actor_user.is_superuser:
        return True
    roles = get_user_roles_for_institution(actor_user, institution)
    return any(r in roles for r in [Role.ADMIN, Role.MODERATOR])


def is_system_admin(actor_user: User) -> bool:
    """
    Determines if actor_user is a system-wide administrator.
    """
    if not actor_user.is_authenticated or not actor_user.is_active:
        return False
    if actor_user.is_superuser:
        return True
    return InstitutionMembership.objects.filter(
        user=actor_user,
        role__in=[Role.ADMIN, Role.MODERATOR],
        is_active=True,
    ).exists()


class IsAuthenticatedAndActive(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active)


class IsSystemAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return is_system_admin(request.user)


class CanManageInstitution(permissions.BasePermission):
    def has_permission(self, request, view):
        institution = getattr(view, "institution", None)
        if not institution:
            institution_id = (
                view.kwargs.get("institution_id")
                or request.query_params.get("institution_id")
                or request.data.get("institution_id")
            )
            if institution_id:
                try:
                    institution = Institution.objects.get(id=institution_id)
                except (Institution.DoesNotExist, ValueError):
                    return False
        if not institution:
            return is_system_admin(request.user)
        return can_manage_institution(request.user, institution)


class CanManageCurriculum(permissions.BasePermission):
    def has_permission(self, request, view):
        institution = getattr(view, "institution", None)
        if not institution:
            institution_id = (
                view.kwargs.get("institution_id")
                or request.query_params.get("institution_id")
                or request.data.get("institution_id")
            )
            if institution_id:
                try:
                    institution = Institution.objects.get(id=institution_id)
                except (Institution.DoesNotExist, ValueError):
                    return False
        if not institution:
            return False
        return can_manage_curriculum(request.user, institution)


class CanAssignAdvisor(permissions.BasePermission):
    def has_permission(self, request, view):
        institution = getattr(view, "institution", None)
        if not institution:
            institution_id = (
                view.kwargs.get("institution_id")
                or request.query_params.get("institution_id")
                or request.data.get("institution_id")
            )
            if institution_id:
                try:
                    institution = Institution.objects.get(id=institution_id)
                except (Institution.DoesNotExist, ValueError):
                    return False
        if not institution:
            return False
        return can_assign_advisor(request.user, institution)
