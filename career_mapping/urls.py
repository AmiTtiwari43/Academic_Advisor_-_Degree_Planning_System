"""
URL Routing for Career Objective and Skill Mapping (Prompt 08D).
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from career_mapping.views import (
    CareerObjectiveViewSet,
    CourseRecommendationsView,
    CourseSkillMappingViewSet,
    SkillGapAnalysisView,
    SkillViewSet,
    StudentCareerPreferenceViewSet,
)

router = DefaultRouter()
router.register(r"skills", SkillViewSet, basename="career-skill")
router.register(r"objectives", CareerObjectiveViewSet, basename="career-objective")
router.register(r"course-skills", CourseSkillMappingViewSet, basename="course-skill-mapping")
router.register(r"preferences", StudentCareerPreferenceViewSet, basename="student-career-preference")

urlpatterns = [
    path("career/skill-gap/", SkillGapAnalysisView.as_view(), name="career-skill-gap"),
    path("career/recommendations/", CourseRecommendationsView.as_view(), name="career-course-recommendations"),
    path("career/", include(router.urls)),
]
