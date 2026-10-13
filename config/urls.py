"""
URL configuration for Academic Advisor & Degree Planning System.
"""

from django.contrib import admin
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from accounts.views import (
    AdvisorAssignmentListView,
    CurriculumManageTestStubView,
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    StudentRecordDetailView,
    UserMeView,
    UserProfileView,
)
from common.views import health_check
from institutions.views import DepartmentListView, InstitutionListView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health-check"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    # Authentication & Profile
    path("api/auth/login/", LoginView.as_view(), name="auth-login"),
    path("api/auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("api/auth/me/", UserMeView.as_view(), name="auth-me"),
    path("api/auth/profile/", UserProfileView.as_view(), name="auth-profile"),
    path(
        "api/auth/password-reset/",
        PasswordResetRequestView.as_view(),
        name="password-reset-request",
    ),
    path(
        "api/auth/password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    # Institutions & Departments
    path("api/institutions/", InstitutionListView.as_view(), name="institution-list"),
    path(
        "api/institutions/<uuid:institution_id>/departments/",
        DepartmentListView.as_view(),
        name="department-list",
    ),
    # Authorization & Record Stubs
    path(
        "api/students/<uuid:student_id>/",
        StudentRecordDetailView.as_view(),
        name="student-record-detail",
    ),
    path(
        "api/advising/assignments/",
        AdvisorAssignmentListView.as_view(),
        name="advising-assignments",
    ),
    path(
        "api/curriculum/manage-test/",
        CurriculumManageTestStubView.as_view(),
        name="curriculum-manage-test",
    ),
]
