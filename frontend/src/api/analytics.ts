import { apiClient } from './client';

export interface TopBottleneck {
  course_code: string;
  course_name: string;
  impacted_students_count: number;
}

export interface AnalyticsOverview {
  total_active_students: number;
  total_plans: number;
  plans_pending_review: number;
  avg_turnaround_hours: number;
  critical_or_high_risk_students: number;
  top_bottlenecks: TopBottleneck[];
}

export interface ProgrammeProgressItem {
  programme_id: string;
  programme_code: string;
  programme_name: string;
  min_credits_required: number;
  total_students: number;
  avg_cgpa: number;
  avg_earned_credits: number;
  bracket_0_25: number;
  bracket_26_50: number;
  bracket_51_75: number;
  bracket_76_100: number;
  near_completion: number;
}

export interface ProgrammeProgressReport {
  report: string;
  generated_at: string;
  total_programmes: number;
  items: ProgrammeProgressItem[];
}

export interface PrerequisiteBlockerItem {
  course_id: string;
  course_code: string;
  course_name: string;
  credits: string;
  impacted_students_count: number;
  total_unpassed_attempts: number;
}

export interface PrerequisiteBlockersReport {
  report: string;
  generated_at: string;
  total_bottlenecks: number;
  items: PrerequisiteBlockerItem[];
}

export interface AdvisorWorkloadItem {
  advisor_id: string;
  advisor_username: string;
  advisor_name: string;
  assigned_advisees_count: number;
  pending_plans_count: number;
  completed_reviews_count: number;
  critical_risk_advisees: number;
  high_risk_advisees: number;
  medium_risk_advisees: number;
  low_risk_advisees: number;
}

export interface AdvisorWorkloadReport {
  report: string;
  generated_at: string;
  total_advisors: number;
  total_active_advisee_assignments: number;
  items: AdvisorWorkloadItem[];
}

export interface ReviewerTurnaroundItem {
  reviewer_id: string;
  reviewer_name: string;
  decisions_count: number;
  avg_turnaround_hours: number;
}

export interface ApprovalTurnaroundReport {
  report: string;
  generated_at: string;
  total_decisions: number;
  avg_turnaround_hours: number;
  min_turnaround_hours: number;
  max_turnaround_hours: number;
  reviewer_breakdown: ReviewerTurnaroundItem[];
}

export interface PlanFunnelStages {
  draft: number;
  submitted: number;
  under_review: number;
  approved: number;
  returned: number;
  rejected: number;
}

export interface PlanFunnelConversions {
  submission_rate_pct: number;
  approval_rate_pct: number;
  rejection_rate_pct: number;
  return_rate_pct: number;
}

export interface PlanFunnelReport {
  report: string;
  generated_at: string;
  total_plans: number;
  stages: PlanFunnelStages;
  conversion_rates: PlanFunnelConversions;
}

export interface RiskLevels {
  critical: number;
  high: number;
  medium: number;
  low: number;
  none: number;
}

export interface AggregateRiskIndicators {
  total_active_indicators: number;
  gpa_risk_count: number;
  repeated_failure_risk_count: number;
  pace_risk_count: number;
  bottleneck_risk_count: number;
  plan_compliance_risk_count: number;
}

export interface ProgrammeRiskBreakdown {
  programme_id: string;
  programme_code: string;
  programme_name: string;
  total_students: number;
  critical_risk_count: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
}

export interface RiskDistributionReport {
  report: string;
  generated_at: string;
  total_students_assessed: number;
  risk_levels: RiskLevels;
  aggregate_indicators: AggregateRiskIndicators;
  programme_breakdown: ProgrammeRiskBreakdown[];
}

export interface ElectiveDemandItem {
  course_id: string;
  course_code: string;
  course_name: string;
  term_code: string;
  term_name: string;
  student_demand_count: number;
  scheduled_capacity: number;
  currently_enrolled: number;
  projected_capacity_deficit: number;
}

export interface ElectiveDemandReport {
  report: string;
  generated_at: string;
  total_items_projected: number;
  items: ElectiveDemandItem[];
}

export const analyticsApi = {
  getOverview: () => apiClient.get<AnalyticsOverview>('/api/analytics/overview/'),

  getProgrammeProgress: (params?: { programme_id?: string }) =>
    apiClient.get<ProgrammeProgressReport>('/api/analytics/programme-progress/', { params }),

  getPrerequisiteBlockers: (params?: { limit?: number }) =>
    apiClient.get<PrerequisiteBlockersReport>('/api/analytics/prerequisite-blockers/', { params }),

  getAdvisorWorkload: (params?: { advisor_id?: string }) =>
    apiClient.get<AdvisorWorkloadReport>('/api/analytics/advisor-workload/', { params }),

  getApprovalTurnaround: (params?: { start_date?: string; end_date?: string }) =>
    apiClient.get<ApprovalTurnaroundReport>('/api/analytics/approval-turnaround/', { params }),

  getPlanFunnel: (params?: { programme_id?: string }) =>
    apiClient.get<PlanFunnelReport>('/api/analytics/plan-funnel/', { params }),

  getRiskDistribution: (params?: { programme_id?: string }) =>
    apiClient.get<RiskDistributionReport>('/api/analytics/risk-distribution/', { params }),

  getElectiveDemand: (params?: { term_id?: string; limit?: number }) =>
    apiClient.get<ElectiveDemandReport>('/api/analytics/elective-demand/', { params }),

  getExportUrl: (endpoint: string, params?: Record<string, string | number | boolean>): string => {
    const searchParams = new URLSearchParams();
    searchParams.set('format', 'csv');
    if (params) {
      Object.entries(params).forEach(([key, val]) => {
        if (val !== undefined && val !== null && val !== '') {
          searchParams.set(key, String(val));
        }
      });
    }
    return `/api/analytics/${endpoint}/?${searchParams.toString()}`;
  },
};
