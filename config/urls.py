"""
URL configuration for Academic Advisor & Degree Planning System.
"""

from django.contrib import admin
from django.urls import include, path, re_path
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
from common.views import GlobalSearchView, health_check, spa_assets_view, spa_index_view
from institutions.views import DepartmentListView, InstitutionListView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health-check"),
    path("api/search/", GlobalSearchView.as_view(), name="global-search"),
    path("api/v1/search/", GlobalSearchView.as_view(), name="global-search-v1"),
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
    # Curriculum and Requirement Authoring
    path("api/v1/", include("curriculum.urls")),
    path("api/", include("curriculum.urls")),
    # Academic Records, Degree Audit and Eligibility
    path("api/v1/", include("academic_records.urls")),
    path("api/", include("academic_records.urls")),
    # Multi-Semester Planning and What-If Simulation
    path("api/v1/", include("planning.urls")),
    path("api/", include("planning.urls")),
    # Career and Skill Mapping
    path("api/v1/", include("career_mapping.urls")),
    path("api/", include("career_mapping.urls")),
    # Advising & Academic Risk Indicators
    path("api/v1/", include("advising.urls")),
    path("api/", include("advising.urls")),
    # Institutional Analytics and Reporting
    path("api/v1/", include("analytics.urls")),
    path("api/", include("analytics.urls")),
    # In-App Notifications Engine
    path("api/v1/", include("notifications.urls")),
    path("api/", include("notifications.urls")),
    # Curriculum-Grounded AI Assistant
    path("api/v1/", include("ai_assistant.urls")),
    path("api/", include("ai_assistant.urls")),
    # Frontend SPA and Assets
    path("assets/<path:path>", spa_assets_view, name="spa-assets"),
    re_path(r"^(?!api/|admin/|static/|assets/).*$", spa_index_view, name="spa-catchall"),
]



