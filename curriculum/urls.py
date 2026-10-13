from django.urls import include, path
from rest_framework.routers import DefaultRouter

from curriculum.views import (
    CourseOfferingViewSet,
    CourseViewSet,
    CreditCategoryViewSet,
    CurriculumVersionViewSet,
    PrerequisiteRuleViewSet,
    ProgrammeViewSet,
    RequirementGroupViewSet,
    RuleTestHarnessView,
    StudentCurriculumAssignmentViewSet,
)

router = DefaultRouter()
router.register(r"programmes", ProgrammeViewSet, basename="programme")
router.register(r"curricula", CurriculumVersionViewSet, basename="curriculum")
router.register(r"courses", CourseViewSet, basename="course")
router.register(r"credit-categories", CreditCategoryViewSet, basename="credit-category")
router.register(r"requirement-groups", RequirementGroupViewSet, basename="requirement-group")
router.register(r"prerequisite-rules", PrerequisiteRuleViewSet, basename="prerequisite-rule")
router.register(r"course-offerings", CourseOfferingViewSet, basename="course-offering")
router.register(
    r"student-assignments",
    StudentCurriculumAssignmentViewSet,
    basename="student-assignment",
)

urlpatterns = [
    path("rules/test-harness/", RuleTestHarnessView.as_view(), name="rule-test-harness"),
    path("", include(router.urls)),
]
