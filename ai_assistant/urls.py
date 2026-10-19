from django.urls import path

from .views import AssistantCapabilitiesView, AssistantQueryView

urlpatterns = [
    path("assistant/query/", AssistantQueryView.as_view(), name="assistant-query"),
    path("assistant/capabilities/", AssistantCapabilitiesView.as_view(), name="assistant-capabilities"),
]
