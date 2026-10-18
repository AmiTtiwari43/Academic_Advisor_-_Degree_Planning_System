import datetime
from typing import Any, Optional

from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, renderers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Role
from accounts.permissions import get_user_roles_for_institution
from analytics.serializers import (
    AdvisorWorkloadReportSerializer,
    AnalyticsOverviewSerializer,
    ApprovalTurnaroundReportSerializer,
    ElectiveDemandReportSerializer,
    PlanFunnelReportSerializer,
    PrerequisiteBlockersReportSerializer,
    ProgrammeProgressReportSerializer,
    RiskDistributionReportSerializer,
)
from analytics.services import (
    generate_report_csv,
    get_advisor_workload_report,
    get_analytics_overview_summary,
    get_approval_turnaround_report,
    get_elective_demand_report,
    get_plan_approval_funnel_report,
    get_prerequisite_blockers_report,
    get_programme_progress_report,
    get_risk_distribution_report,
)
from institutions.models import Institution


class CSVRenderer(renderers.BaseRenderer):
    media_type = "text/csv"
    format = "csv"

    def render(
        self,
        data: Any,
        accepted_media_type: Optional[str] = None,
        renderer_context: Optional[dict[str, Any]] = None,
    ) -> Any:
        return data


class BaseAnalyticsReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    renderer_classes = [renderers.JSONRenderer, CSVRenderer, renderers.BrowsableAPIRenderer]



def _get_active_institution(request: Request, institution_id: Optional[str] = None) -> Institution:
    """Helper to resolve and validate the request institution context."""
    user = request.user
    if institution_id:
        return get_object_or_404(Institution, id=institution_id)

    header_inst = request.headers.get("X-Institution-ID")
    if header_inst:
        try:
            return get_object_or_404(Institution, id=header_inst)
        except (ValueError, ValidationError):
            pass

    membership = user.institution_memberships.filter(is_active=True).first()
    if membership:
        return membership.institution

    raise PermissionDenied("Active institutional context required.")


def _check_analytics_authorization(request: Request, institution: Institution) -> set[str]:
    """
    Enforces role-based permissions for institutional analytics.
    Students are strictly forbidden (403 Forbidden).
    Cross-institution users are denied with 404 Not Found to prevent data existence leakage.
    """
    roles = get_user_roles_for_institution(request.user, institution)
    if not roles:
        raise Http404("Institution not found.")

    roles_set = set(roles)
    allowed_roles = {
        Role.ADVISOR.value,
        Role.COORDINATOR.value,
        Role.HOD.value,
        Role.ADMIN.value,
    }
    if not roles_set.intersection(allowed_roles):
        raise PermissionDenied("Students are not authorized to access institutional analytics.")

    return roles_set



def _format_csv_response(report_type: str, filename_prefix: str, headers: list[str], rows: list[list[Any]]) -> HttpResponse:
    csv_content = generate_report_csv(report_type, headers, rows)
    timestamp = datetime.date.today().isoformat()
    response = HttpResponse(csv_content, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename_prefix}_{timestamp}.csv"'
    return response


class AnalyticsOverviewView(BaseAnalyticsReportView):
    """
    Executive dashboard metrics: active students, pending reviews, turnaround, and top bottlenecks.
    """
    serializer_class = AnalyticsOverviewSerializer

    @extend_schema(
        summary="Analytics Overview Summary",
        description="Returns top-level institutional metrics and bottleneck highlights.",
        responses={200: AnalyticsOverviewSerializer},
    )
    def get(self, request: Request) -> Response:
        institution = _get_active_institution(request)
        _check_analytics_authorization(request, institution)
        data = get_analytics_overview_summary(institution)
        serializer = self.serializer_class(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProgrammeProgressReportView(BaseAnalyticsReportView):
    """
    Returns student degree-progress distribution by programme (0-25%, 26-50%, 51-75%, 76-100%).
    Supports ?format=csv export.
    """
    serializer_class = ProgrammeProgressReportSerializer

    @extend_schema(
        summary="Programme Progress Distribution",
        description="Returns student degree completion brackets and GPA aggregates by programme.",
        parameters=[
            OpenApiParameter("programme_id", type=str, required=False, description="Filter by programme ID"),
            OpenApiParameter("format", type=str, required=False, description="Set to 'csv' for export"),
        ],
        responses={200: ProgrammeProgressReportSerializer},
    )
    def get(self, request: Request) -> Response | HttpResponse:
        institution = _get_active_institution(request)
        _check_analytics_authorization(request, institution)

        programme_id = request.query_params.get("programme_id")
        data = get_programme_progress_report(institution, programme_id=programme_id)

        if request.query_params.get("format") == "csv" or request.query_params.get("export") == "csv":
            headers = [
                "Programme Code",
                "Programme Name",
                "Min Credits",
                "Total Students",
                "Avg CGPA",
                "Avg Earned Credits",
                "0-25% Progress",
                "26-50% Progress",
                "51-75% Progress",
                "76-100% Progress",
                "Near Completion (>=90%)",
            ]
            rows = [
                [
                    item["programme_code"],
                    item["programme_name"],
                    item["min_credits_required"],
                    item["total_students"],
                    item["avg_cgpa"],
                    item["avg_earned_credits"],
                    item["bracket_0_25"],
                    item["bracket_26_50"],
                    item["bracket_51_75"],
                    item["bracket_76_100"],
                    item["near_completion"],
                ]
                for item in data["items"]
            ]
            return _format_csv_response("Programme Progress Report", "programme_progress", headers, rows)

        serializer = self.serializer_class(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PrerequisiteBlockersReportView(BaseAnalyticsReportView):
    """
    Returns top courses with unpassed attempts blocking degree progression.
    Supports ?format=csv export.
    """
    serializer_class = PrerequisiteBlockersReportSerializer

    @extend_schema(
        summary="Prerequisite Bottlenecks Report",
        description="Aggregates courses with unpassed attempts causing graduation delays.",
        parameters=[
            OpenApiParameter("limit", type=int, required=False, description="Number of blockers to return (default 20)"),
            OpenApiParameter("format", type=str, required=False, description="Set to 'csv' for export"),
        ],
        responses={200: PrerequisiteBlockersReportSerializer},
    )
    def get(self, request: Request) -> Response | HttpResponse:
        institution = _get_active_institution(request)
        _check_analytics_authorization(request, institution)

        limit_param = request.query_params.get("limit")
        limit = int(limit_param) if limit_param and limit_param.isdigit() else 20
        data = get_prerequisite_blockers_report(institution, limit=limit)

        if request.query_params.get("format") == "csv" or request.query_params.get("export") == "csv":
            headers = ["Course Code", "Course Name", "Credits", "Impacted Students Count", "Total Unpassed Attempts"]
            rows = [
                [
                    item["course_code"],
                    item["course_name"],
                    item["credits"],
                    item["impacted_students_count"],
                    item["total_unpassed_attempts"],
                ]
                for item in data["items"]
            ]
            return _format_csv_response("Prerequisite Blockers Report", "prerequisite_blockers", headers, rows)

        serializer = self.serializer_class(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AdvisorWorkloadReportView(BaseAnalyticsReportView):
    """
    Returns advising loads, pending reviews, and advisee risk level breakdown per advisor.
    Supports ?format=csv export.
    """
    serializer_class = AdvisorWorkloadReportSerializer

    @extend_schema(
        summary="Advisor Workload Report",
        description="Computes assigned advisees, pending plan reviews, completed reviews, and risk levels per advisor.",
        parameters=[
            OpenApiParameter("advisor_id", type=str, required=False, description="Filter by advisor User ID"),
            OpenApiParameter("format", type=str, required=False, description="Set to 'csv' for export"),
        ],
        responses={200: AdvisorWorkloadReportSerializer},
    )
    def get(self, request: Request) -> Response | HttpResponse:
        institution = _get_active_institution(request)
        roles = _check_analytics_authorization(request, institution)

        advisor_id = request.query_params.get("advisor_id")
        # If user is strictly an advisor (not Coordinator/Admin), default or scope to their own workload
        if Role.ADVISOR.value in roles and not roles.intersection(
            {Role.COORDINATOR.value, Role.HOD.value, Role.ADMIN.value}
        ):
            advisor_id = str(request.user.id)

        data = get_advisor_workload_report(institution, advisor_id=advisor_id)

        if request.query_params.get("format") == "csv" or request.query_params.get("export") == "csv":
            headers = [
                "Advisor Username",
                "Advisor Name",
                "Active Advisees",
                "Pending Plan Reviews",
                "Completed Reviews",
                "Critical Risk Advisees",
                "High Risk Advisees",
                "Medium Risk Advisees",
                "Low Risk Advisees",
            ]
            rows = [
                [
                    item["advisor_username"],
                    item["advisor_name"],
                    item["assigned_advisees_count"],
                    item["pending_plans_count"],
                    item["completed_reviews_count"],
                    item["critical_risk_advisees"],
                    item["high_risk_advisees"],
                    item["medium_risk_advisees"],
                    item["low_risk_advisees"],
                ]
                for item in data["items"]
            ]
            return _format_csv_response("Advisor Workload Report", "advisor_workload", headers, rows)

        serializer = self.serializer_class(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ApprovalTurnaroundReportView(BaseAnalyticsReportView):
    """
    Returns turnaround metrics from plan submission to advisor decision.
    Supports ?format=csv export.
    """
    serializer_class = ApprovalTurnaroundReportSerializer

    @extend_schema(
        summary="Approval Turnaround Metrics",
        description="Calculates turnaround hours from plan submission to review decision.",
        parameters=[
            OpenApiParameter("start_date", type=str, required=False, description="YYYY-MM-DD filter"),
            OpenApiParameter("end_date", type=str, required=False, description="YYYY-MM-DD filter"),
            OpenApiParameter("format", type=str, required=False, description="Set to 'csv' for export"),
        ],
        responses={200: ApprovalTurnaroundReportSerializer},
    )
    def get(self, request: Request) -> Response | HttpResponse:
        institution = _get_active_institution(request)
        _check_analytics_authorization(request, institution)

        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")
        start_date = datetime.date.fromisoformat(start_date_str) if start_date_str else None
        end_date = datetime.date.fromisoformat(end_date_str) if end_date_str else None

        data = get_approval_turnaround_report(institution, start_date=start_date, end_date=end_date)

        if request.query_params.get("format") == "csv" or request.query_params.get("export") == "csv":
            headers = ["Reviewer Name", "Decisions Count", "Avg Turnaround Hours"]
            rows = [
                [
                    item["reviewer_name"],
                    item["decisions_count"],
                    item["avg_turnaround_hours"],
                ]
                for item in data["reviewer_breakdown"]
            ]
            return _format_csv_response("Approval Turnaround Report", "approval_turnaround", headers, rows)

        serializer = self.serializer_class(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PlanFunnelReportView(BaseAnalyticsReportView):
    """
    Returns plan lifecycle funnel stages and conversion rates.
    """
    serializer_class = PlanFunnelReportSerializer

    @extend_schema(
        summary="Plan Approval Funnel",
        description="Returns plan lifecycle status breakdown and conversion rates.",
        parameters=[
            OpenApiParameter("programme_id", type=str, required=False, description="Filter by programme ID"),
            OpenApiParameter("format", type=str, required=False, description="Set to 'csv' for export"),
        ],
        responses={200: PlanFunnelReportSerializer},
    )
    def get(self, request: Request) -> Response | HttpResponse:
        institution = _get_active_institution(request)
        _check_analytics_authorization(request, institution)

        programme_id = request.query_params.get("programme_id")
        data = get_plan_approval_funnel_report(institution, programme_id=programme_id)

        if request.query_params.get("format") == "csv" or request.query_params.get("export") == "csv":
            headers = ["Stage", "Count"]
            rows = [[stage, count] for stage, count in data["stages"].items()]
            return _format_csv_response("Plan Approval Funnel", "plan_funnel", headers, rows)

        serializer = self.serializer_class(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RiskDistributionReportView(BaseAnalyticsReportView):
    """
    Returns institutional academic risk distribution consuming Phase 08E risk profiles.
    Supports ?format=csv export.
    """
    serializer_class = RiskDistributionReportSerializer

    @extend_schema(
        summary="Risk Distribution Report",
        description="Returns distribution of academic risk indicators and levels across assessed students.",
        parameters=[
            OpenApiParameter("programme_id", type=str, required=False, description="Filter by programme ID"),
            OpenApiParameter("format", type=str, required=False, description="Set to 'csv' for export"),
        ],
        responses={200: RiskDistributionReportSerializer},
    )
    def get(self, request: Request) -> Response | HttpResponse:
        institution = _get_active_institution(request)
        _check_analytics_authorization(request, institution)

        programme_id = request.query_params.get("programme_id")
        data = get_risk_distribution_report(institution, programme_id=programme_id)

        if request.query_params.get("format") == "csv" or request.query_params.get("export") == "csv":
            headers = [
                "Programme Code",
                "Programme Name",
                "Total Students",
                "Critical Risk",
                "High Risk",
                "Medium Risk",
                "Low Risk",
            ]
            rows = [
                [
                    item["programme_code"],
                    item["programme_name"],
                    item["total_students"],
                    item["critical_risk_count"],
                    item["high_risk_count"],
                    item["medium_risk_count"],
                    item["low_risk_count"],
                ]
                for item in data["programme_breakdown"]
            ]
            return _format_csv_response("Academic Risk Distribution Report", "risk_distribution", headers, rows)

        serializer = self.serializer_class(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ElectiveDemandReportView(BaseAnalyticsReportView):
    """
    Returns planned elective demand in upcoming terms vs scheduled offering capacity.
    Supports ?format=csv export.
    """
    serializer_class = ElectiveDemandReportSerializer

    @extend_schema(
        summary="Elective Course Demand Projection",
        description="Aggregates student planned electives across future terms vs course offering capacities.",
        parameters=[
            OpenApiParameter("term_id", type=str, required=False, description="Filter by academic term ID"),
            OpenApiParameter("limit", type=int, required=False, description="Number of items to return"),
            OpenApiParameter("format", type=str, required=False, description="Set to 'csv' for export"),
        ],
        responses={200: ElectiveDemandReportSerializer},
    )
    def get(self, request: Request) -> Response | HttpResponse:
        institution = _get_active_institution(request)
        _check_analytics_authorization(request, institution)

        term_id = request.query_params.get("term_id")
        limit_param = request.query_params.get("limit")
        limit = int(limit_param) if limit_param and limit_param.isdigit() else 25

        data = get_elective_demand_report(institution, term_id=term_id, limit=limit)

        if request.query_params.get("format") == "csv" or request.query_params.get("export") == "csv":
            headers = [
                "Course Code",
                "Course Name",
                "Term Code",
                "Term Name",
                "Student Demand Count",
                "Scheduled Capacity",
                "Currently Enrolled",
                "Projected Capacity Deficit",
            ]
            rows = [
                [
                    item["course_code"],
                    item["course_name"],
                    item["term_code"],
                    item["term_name"],
                    item["student_demand_count"],
                    item["scheduled_capacity"],
                    item["currently_enrolled"],
                    item["projected_capacity_deficit"],
                ]
                for item in data["items"]
            ]
            return _format_csv_response("Elective Demand Report", "elective_demand", headers, rows)

        serializer = self.serializer_class(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
