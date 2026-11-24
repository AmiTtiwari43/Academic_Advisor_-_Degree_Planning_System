from typing import Optional

from django.db import transaction
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from accounts.models import AdvisorAssignment, InstitutionMembership, Role, UserProfile
from institutions.models import Institution


def invalidate_user_sessions(user: User) -> None:
    """
    Terminates all active Django sessions associated with the given user.
    """
    for session in Session.objects.iterator():
        try:
            data = session.get_decoded()
            if str(data.get("_auth_user_id")) == str(user.pk):
                session.delete()
        except Exception:
            continue


def authenticate_and_login(request, username: str, password: str) -> User:
    """
    Authenticates user credentials and verifies active membership.
    On success, starts a session; on failure, raises ValidationError.
    Supports both username and institutional email identifier.
    """
    user = authenticate(request, username=username, password=password)
    if not user and "@" in username:
        matched_user = User.objects.filter(email__iexact=username).first()
        if matched_user:
            user = authenticate(request, username=matched_user.username, password=password)

    if not user or not user.is_active:
        raise ValidationError("Invalid credentials.")

    if not user.is_superuser:
        has_active_membership = InstitutionMembership.objects.filter(
            user=user,
            is_active=True,
        ).exists()
        if not has_active_membership:
            raise ValidationError("User has no active institutional membership.")

    login(request, user)
    return user


def logout_user(request) -> None:
    """
    Logs out the current session.
    """
    logout(request)


def request_password_reset(email: str) -> None:
    """
    Initiates a password reset for the specified email.
    Always succeeds without error to prevent user enumeration.
    """
    users = User.objects.filter(email__iexact=email.strip(), is_active=True)
    for user in users:
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        send_mail(
            subject="Password Reset Request - Academic Advisor System",
            message=f"Use token {token} and UID {uid} to reset your password.",
            from_email="noreply@degreeplanning.local",
            recipient_list=[user.email],
            fail_silently=True,
        )


def confirm_password_reset(uidb64: str, token: str, new_password: str) -> None:
    """
    Validates token and updates user password, terminating all prior sessions.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        raise ValidationError("Invalid password reset token.")

    if not default_token_generator.check_token(user, token):
        raise ValidationError("Invalid or expired password reset token.")

    validate_password(new_password, user=user)
    user.set_password(new_password)
    user.save()
    invalidate_user_sessions(user)


@transaction.atomic
def update_user_profile(
    user: User,
    phone_number: Optional[str] = None,
    preferred_name: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    email: Optional[str] = None,
) -> UserProfile:
    """
    Updates profile fields for a user atomically. Ignores any privileged attributes.
    """
    profile, _ = UserProfile.objects.get_or_create(user=user)
    if phone_number is not None:
        profile.phone_number = phone_number.strip()
    if preferred_name is not None:
        profile.preferred_name = preferred_name.strip()
    profile.save()

    user_updated_fields = []
    if first_name is not None:
        user.first_name = first_name.strip()
        user_updated_fields.append("first_name")
    if last_name is not None:
        user.last_name = last_name.strip()
        user_updated_fields.append("last_name")
    if email is not None and email.strip():
        user.email = email.strip()
        user_updated_fields.append("email")
    if user_updated_fields:
        user.save(update_fields=user_updated_fields)

    return profile


def set_user_active_status(user: User, is_active: bool) -> None:
    """
    Activates or deactivates a user account.
    Deactivation immediately terminates all active user sessions.
    """
    user.is_active = is_active
    user.save(update_fields=["is_active"])
    if not is_active:
        InstitutionMembership.objects.filter(user=user).update(is_active=False)
        invalidate_user_sessions(user)


def set_membership_active_status(membership: InstitutionMembership, is_active: bool) -> None:
    """
    Updates membership status and revokes user sessions if no active memberships remain.
    """
    membership.is_active = is_active
    membership.save(update_fields=["is_active"])
    if not is_active:
        user = membership.user
        if (
            not user.is_superuser
            and not InstitutionMembership.objects.filter(user=user, is_active=True).exists()
        ):
            invalidate_user_sessions(user)


def assign_advisor(
    institution: Institution,
    advisor_membership: InstitutionMembership,
    student_membership: InstitutionMembership,
) -> AdvisorAssignment:
    """
    Creates an advising relationship within the specified institution.
    """
    if advisor_membership.institution_id != institution.id:
        raise ValidationError("Advisor does not belong to the institution.")
    if student_membership.institution_id != institution.id:
        raise ValidationError("Student does not belong to the institution.")
    if advisor_membership.role != Role.ADVISOR:
        raise ValidationError("Assigned advisor must have ADVISOR role.")
    if student_membership.role != Role.STUDENT:
        raise ValidationError("Assigned student must have STUDENT role.")
    if advisor_membership.user_id == student_membership.user_id:
        raise ValidationError("Cannot assign advisor to themselves.")

    assignment, _ = AdvisorAssignment.objects.update_or_create(
        institution=institution,
        advisor=advisor_membership,
        student=student_membership,
        defaults={"is_active": True},
    )
    return assignment
