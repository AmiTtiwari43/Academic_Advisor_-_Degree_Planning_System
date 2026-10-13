from django.contrib import admin

from accounts.models import AdvisorAssignment, InstitutionMembership, UserProfile
from accounts.permissions import is_system_admin


# Restrict Django admin to system administrators
def restricted_admin_has_permission(request):
    if not request.user or not request.user.is_authenticated or not request.user.is_active:
        return False
    if request.user.is_superuser:
        return True
    return bool(request.user.is_staff and is_system_admin(request.user))


admin.site.has_permission = restricted_admin_has_permission  # type: ignore[method-assign]


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "preferred_name", "phone_number", "created_at")
    search_fields = ("user__username", "user__email", "preferred_name")


@admin.register(InstitutionMembership)
class InstitutionMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "institution", "role", "is_active", "created_at")
    list_filter = ("institution", "role", "is_active")
    search_fields = ("user__username", "user__email")


@admin.register(AdvisorAssignment)
class AdvisorAssignmentAdmin(admin.ModelAdmin):
    list_display = ("advisor", "student", "institution", "is_active", "assigned_at")
    list_filter = ("institution", "is_active")
    search_fields = ("advisor__user__username", "student__user__username")
