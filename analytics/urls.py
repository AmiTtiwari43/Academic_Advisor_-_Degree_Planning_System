from django.urls import path

from analytics.views import (
    AdvisorWorkloadReportView,
    AnalyticsOverviewView,
    ApprovalTurnaroundReportView,
    ElectiveDemandReportView,
    PlanFunnelReportView,
    PrerequisiteBlockersReportView,
    ProgrammeProgressReportView,
    RiskDistributionReportView,
)

urlpatterns = [
    path("analytics/overview/", AnalyticsOverviewView.as_view(), name="analytics-overview"),
    path("analytics/programme-progress/", ProgrammeProgressReportView.as_view(), name="analytics-programme-progress"),
    path("analytics/prerequisite-blockers/", PrerequisiteBlockersReportView.as_view(), name="analytics-prerequisite-blockers"),
    path("analytics/advisor-workload/", AdvisorWorkloadReportView.as_view(), name="analytics-advisor-workload"),
    path("analytics/approval-turnaround/", ApprovalTurnaroundReportView.as_view(), name="analytics-approval-turnaround"),
    path("analytics/plan-funnel/", PlanFunnelReportView.as_view(), name="analytics-plan-funnel"),
    path("analytics/risk-distribution/", RiskDistributionReportView.as_view(), name="analytics-risk-distribution"),
    path("analytics/elective-demand/", ElectiveDemandReportView.as_view(), name="analytics-elective-demand"),
]
