from django.urls import path
from rest_framework.routers import DefaultRouter

from planning.views import AdvisorQueueView, PlanViewSet, WhatIfSimulationView

router = DefaultRouter()
router.register(r"plans", PlanViewSet, basename="degree-plan")

urlpatterns = [
    path("plans/what-if/", WhatIfSimulationView.as_view(), name="plan-what-if"),
    path("advising/queue/", AdvisorQueueView.as_view(), name="advising-queue"),
] + router.urls

