from django.urls import path
from rest_framework.routers import DefaultRouter

from advising.views import (
    InstitutionRiskSummaryView,
    PlanRiskView,
    RiskAcknowledgmentViewSet,
    StudentRiskEvaluateView,
    StudentRiskProfileView,
)

router = DefaultRouter()
router.register(r"advising/risks/acknowledgments", RiskAcknowledgmentViewSet, basename="risk-acknowledgment")

urlpatterns = [
    path("advising/students/<str:student_id>/risk/", StudentRiskProfileView.as_view(), name="student-risk-profile"),
    path("advising/students/<str:student_id>/risk/evaluate/", StudentRiskEvaluateView.as_view(), name="student-risk-evaluate"),
    path("plans/<uuid:plan_id>/risk/", PlanRiskView.as_view(), name="plan-risk"),
    path("advising/risks/summary/", InstitutionRiskSummaryView.as_view(), name="institution-risk-summary"),
] + router.urls
