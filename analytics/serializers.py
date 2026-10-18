from rest_framework import serializers


class ProgrammeProgressItemSerializer(serializers.Serializer):
    programme_id = serializers.CharField()
    programme_code = serializers.CharField()
    programme_name = serializers.CharField()
    min_credits_required = serializers.FloatField()
    total_students = serializers.IntegerField()
    avg_cgpa = serializers.FloatField()
    avg_earned_credits = serializers.FloatField()
    bracket_0_25 = serializers.IntegerField()
    bracket_26_50 = serializers.IntegerField()
    bracket_51_75 = serializers.IntegerField()
    bracket_76_100 = serializers.IntegerField()
    near_completion = serializers.IntegerField()


class ProgrammeProgressReportSerializer(serializers.Serializer):
    report = serializers.CharField(default="programme_progress")
    total_programmes = serializers.IntegerField()
    total_students_enrolled = serializers.IntegerField()
    items = ProgrammeProgressItemSerializer(many=True)


class PrerequisiteBlockerItemSerializer(serializers.Serializer):
    course_id = serializers.CharField()
    course_code = serializers.CharField()
    course_name = serializers.CharField()
    credits = serializers.FloatField()
    impacted_students_count = serializers.IntegerField()
    total_unpassed_attempts = serializers.IntegerField()


class PrerequisiteBlockersReportSerializer(serializers.Serializer):
    report = serializers.CharField(default="prerequisite_blockers")
    total_blockers_identified = serializers.IntegerField()
    items = PrerequisiteBlockerItemSerializer(many=True)


class AdvisorWorkloadItemSerializer(serializers.Serializer):
    advisor_id = serializers.CharField()
    advisor_username = serializers.CharField()
    advisor_name = serializers.CharField()
    assigned_advisees_count = serializers.IntegerField()
    pending_plans_count = serializers.IntegerField()
    completed_reviews_count = serializers.IntegerField()
    critical_risk_advisees = serializers.IntegerField()
    high_risk_advisees = serializers.IntegerField()
    medium_risk_advisees = serializers.IntegerField()
    low_risk_advisees = serializers.IntegerField()


class AdvisorWorkloadReportSerializer(serializers.Serializer):
    report = serializers.CharField(default="advisor_workload")
    total_advisors = serializers.IntegerField()
    total_active_advisee_assignments = serializers.IntegerField()
    total_pending_reviews = serializers.IntegerField()
    items = AdvisorWorkloadItemSerializer(many=True)


class ReviewerTurnaroundItemSerializer(serializers.Serializer):
    reviewer_id = serializers.CharField()
    reviewer_name = serializers.CharField()
    decisions_count = serializers.IntegerField()
    avg_turnaround_hours = serializers.FloatField()


class ActionTurnaroundItemSerializer(serializers.Serializer):
    action = serializers.CharField()
    count = serializers.IntegerField()
    avg_turnaround_hours = serializers.FloatField()


class ApprovalTurnaroundReportSerializer(serializers.Serializer):
    report = serializers.CharField(default="approval_turnaround")
    total_decisions = serializers.IntegerField()
    avg_turnaround_hours = serializers.FloatField()
    min_turnaround_hours = serializers.FloatField()
    max_turnaround_hours = serializers.FloatField()
    reviewer_breakdown = ReviewerTurnaroundItemSerializer(many=True)
    action_breakdown = ActionTurnaroundItemSerializer(many=True)


class PlanFunnelReportSerializer(serializers.Serializer):
    report = serializers.CharField(default="plan_funnel")
    total_plans = serializers.IntegerField()
    stages = serializers.DictField(child=serializers.IntegerField())
    conversion_rates = serializers.DictField(child=serializers.FloatField())


class ProgrammeRiskItemSerializer(serializers.Serializer):
    programme_id = serializers.CharField()
    programme_code = serializers.CharField()
    programme_name = serializers.CharField()
    total_students = serializers.IntegerField()
    critical_risk_count = serializers.IntegerField()
    high_risk_count = serializers.IntegerField()
    medium_risk_count = serializers.IntegerField()
    low_risk_count = serializers.IntegerField()


class RiskDistributionReportSerializer(serializers.Serializer):
    report = serializers.CharField(default="risk_distribution")
    total_students_assessed = serializers.IntegerField()
    risk_levels = serializers.DictField(child=serializers.IntegerField())
    aggregate_indicators = serializers.DictField(child=serializers.FloatField())
    programme_breakdown = ProgrammeRiskItemSerializer(many=True)


class ElectiveDemandItemSerializer(serializers.Serializer):
    course_id = serializers.CharField()
    course_code = serializers.CharField()
    course_name = serializers.CharField()
    term_code = serializers.CharField()
    term_name = serializers.CharField()
    student_demand_count = serializers.IntegerField()
    scheduled_capacity = serializers.IntegerField()
    currently_enrolled = serializers.IntegerField()
    projected_capacity_deficit = serializers.IntegerField()


class ElectiveDemandReportSerializer(serializers.Serializer):
    report = serializers.CharField(default="elective_demand")
    total_items_projected = serializers.IntegerField()
    items = ElectiveDemandItemSerializer(many=True)


class AnalyticsOverviewSerializer(serializers.Serializer):
    total_active_students = serializers.IntegerField()
    total_plans = serializers.IntegerField()
    plans_pending_review = serializers.IntegerField()
    critical_or_high_risk_students = serializers.IntegerField()
    avg_approval_turnaround_hours = serializers.FloatField()
    top_bottlenecks = PrerequisiteBlockerItemSerializer(many=True)
