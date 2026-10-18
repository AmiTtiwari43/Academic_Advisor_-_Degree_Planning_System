import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AnalyticsDashboardPage } from '../AnalyticsDashboardPage';
import {
  analyticsApi,
  AnalyticsOverview,
  ProgrammeProgressReport,
  PrerequisiteBlockersReport,
  AdvisorWorkloadReport,
  ApprovalTurnaroundReport,
  PlanFunnelReport,
  RiskDistributionReport,
  ElectiveDemandReport,
} from '../../api/analytics';
import * as authContext from '../../context/AuthContext';

const mockOverview: AnalyticsOverview = {
  total_active_students: 150,
  total_plans: 120,
  plans_pending_review: 15,
  avg_turnaround_hours: 14.5,
  critical_or_high_risk_students: 12,
  top_bottlenecks: [
    {
      course_code: 'CS201',
      course_name: 'Data Structures',
      impacted_students_count: 24,
    },
  ],
};

const mockProgrammeProgress: ProgrammeProgressReport = {
  report: 'programme_progress',
  generated_at: '2026-10-19T00:00:00Z',
  total_programmes: 1,
  items: [
    {
      programme_id: 'prog-1',
      programme_code: 'CS-BS',
      programme_name: 'B.S. in Computer Science',
      min_credits_required: 120,
      total_students: 150,
      avg_cgpa: 3.45,
      avg_earned_credits: 75.0,
      bracket_0_25: 30,
      bracket_26_50: 40,
      bracket_51_75: 50,
      bracket_76_100: 30,
      near_completion: 18,
    },
  ],
};

const mockBlockers: PrerequisiteBlockersReport = {
  report: 'prerequisite_blockers',
  generated_at: '2026-10-19T00:00:00Z',
  total_bottlenecks: 1,
  items: [
    {
      course_id: 'c-201',
      course_code: 'CS201',
      course_name: 'Data Structures',
      credits: '4.00',
      impacted_students_count: 24,
      total_unpassed_attempts: 28,
    },
  ],
};

const mockWorkload: AdvisorWorkloadReport = {
  report: 'advisor_workload',
  generated_at: '2026-10-19T00:00:00Z',
  total_advisors: 1,
  total_active_advisee_assignments: 45,
  items: [
    {
      advisor_id: 'adv-1',
      advisor_username: 'advisor_sarah',
      advisor_name: 'Dr. Sarah Connor',
      assigned_advisees_count: 45,
      pending_plans_count: 5,
      completed_reviews_count: 40,
      critical_risk_advisees: 2,
      high_risk_advisees: 4,
      medium_risk_advisees: 8,
      low_risk_advisees: 31,
    },
  ],
};

const mockTurnaround: ApprovalTurnaroundReport = {
  report: 'approval_turnaround',
  generated_at: '2026-10-19T00:00:00Z',
  total_decisions: 40,
  avg_turnaround_hours: 14.5,
  min_turnaround_hours: 2.0,
  max_turnaround_hours: 48.0,
  reviewer_breakdown: [
    {
      reviewer_id: 'adv-1',
      reviewer_name: 'Dr. Sarah Connor',
      decisions_count: 40,
      avg_turnaround_hours: 14.5,
    },
  ],
};

const mockFunnel: PlanFunnelReport = {
  report: 'plan_funnel',
  generated_at: '2026-10-19T00:00:00Z',
  total_plans: 100,
  stages: {
    draft: 20,
    submitted: 30,
    under_review: 10,
    approved: 35,
    returned: 3,
    rejected: 2,
  },
  conversion_rates: {
    submission_rate_pct: 80.0,
    approval_rate_pct: 87.5,
    rejection_rate_pct: 5.0,
    return_rate_pct: 7.5,
  },
};

const mockRisk: RiskDistributionReport = {
  report: 'risk_distribution',
  generated_at: '2026-10-19T00:00:00Z',
  total_students_assessed: 150,
  risk_levels: {
    critical: 4,
    high: 8,
    medium: 22,
    low: 100,
    none: 16,
  },
  aggregate_indicators: {
    total_active_indicators: 45,
    gpa_risk_count: 10,
    repeated_failure_risk_count: 12,
    pace_risk_count: 8,
    bottleneck_risk_count: 9,
    plan_compliance_risk_count: 6,
  },
  programme_breakdown: [
    {
      programme_id: 'prog-1',
      programme_code: 'CS-BS',
      programme_name: 'B.S. in Computer Science',
      total_students: 150,
      critical_risk_count: 4,
      high_risk_count: 8,
      medium_risk_count: 22,
      low_risk_count: 116,
    },
  ],
};

const mockDemand: ElectiveDemandReport = {
  report: 'elective_demand',
  generated_at: '2026-10-19T00:00:00Z',
  total_items_projected: 1,
  items: [
    {
      course_id: 'c-401',
      course_code: 'AI401',
      course_name: 'Machine Learning',
      term_code: 'FA2026',
      term_name: 'Fall 2026',
      student_demand_count: 60,
      scheduled_capacity: 40,
      currently_enrolled: 30,
      projected_capacity_deficit: 20,
    },
  ],
};

describe('AnalyticsDashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      user: {
        id: '1',
        username: 'coordinator_user',
        email: 'coord@univ.edu',
        first_name: 'Coordinator',
        last_name: 'User',
        preferred_name: '',
        phone_number: '',
        memberships: [],
        is_staff: true,
        is_superuser: false,
      },
      activeMembership: null,
      activeRole: 'COORDINATOR',
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
      switchMembership: vi.fn(),
      hasRole: () => true,
      refreshUser: vi.fn(),
    });

    vi.spyOn(analyticsApi, 'getOverview').mockResolvedValue(mockOverview);
    vi.spyOn(analyticsApi, 'getProgrammeProgress').mockResolvedValue(mockProgrammeProgress);
    vi.spyOn(analyticsApi, 'getPrerequisiteBlockers').mockResolvedValue(mockBlockers);
    vi.spyOn(analyticsApi, 'getAdvisorWorkload').mockResolvedValue(mockWorkload);
    vi.spyOn(analyticsApi, 'getApprovalTurnaround').mockResolvedValue(mockTurnaround);
    vi.spyOn(analyticsApi, 'getPlanFunnel').mockResolvedValue(mockFunnel);
    vi.spyOn(analyticsApi, 'getRiskDistribution').mockResolvedValue(mockRisk);
    vi.spyOn(analyticsApi, 'getElectiveDemand').mockResolvedValue(mockDemand);
  });

  it('renders overview metrics and bottleneck alert', async () => {
    render(<AnalyticsDashboardPage />);

    expect(await screen.findByText('Institutional Analytics & Reporting')).toBeInTheDocument();
    expect(await screen.findByText('Institutional enrolled count')).toBeInTheDocument();
    expect(screen.getByText('120')).toBeInTheDocument(); // Degree plans
    expect(screen.getByText(/14.5/)).toBeInTheDocument(); // Turnaround hours
    expect(screen.getByText(/CS201/)).toBeInTheDocument(); // Bottleneck alert
  });

  it('renders the programme progress report table', async () => {
    render(<AnalyticsDashboardPage />);

    expect(await screen.findByText('CS-BS')).toBeInTheDocument();
    expect(screen.getByText('B.S. in Computer Science')).toBeInTheDocument();
    expect(screen.getByText('3.45')).toBeInTheDocument();
    expect(screen.getByText('18')).toBeInTheDocument(); // Near grad
  });

  it('switches between tabs and loads corresponding report data', async () => {
    render(<AnalyticsDashboardPage />);

    // 1. Click Prerequisite Blockers tab
    const blockersTab = await screen.findByRole('tab', { name: /Prerequisite Blockers/i });
    fireEvent.click(blockersTab);

    expect(await screen.findByText('Failed/Unpassed Attempts')).toBeInTheDocument();
    expect(await screen.findByText('24 students')).toBeInTheDocument();

    // 2. Click Advisor Workload tab
    const workloadTab = screen.getByRole('tab', { name: /Advisor Workload/i });
    fireEvent.click(workloadTab);

    expect(await screen.findByText('Dr. Sarah Connor')).toBeInTheDocument();
    expect(screen.getByText('45')).toBeInTheDocument();

    // 3. Click Turnaround Times tab
    const turnaroundTab = screen.getByRole('tab', { name: /Turnaround Times/i });
    fireEvent.click(turnaroundTab);

    expect(await screen.findByText('Fastest Decision')).toBeInTheDocument();
    expect(screen.getByText('Total Decisions Made')).toBeInTheDocument();

    // 4. Click Plan Funnel tab
    const funnelTab = screen.getByRole('tab', { name: /Plan Funnel/i });
    fireEvent.click(funnelTab);

    expect(await screen.findByText('80.0%')).toBeInTheDocument();
    expect(screen.getByText('Plan Pipeline Volume by Status')).toBeInTheDocument();

    // 5. Click Graduation Risk tab
    const riskTab = screen.getByRole('tab', { name: /Graduation Risk/i });
    fireEvent.click(riskTab);

    expect(await screen.findByText('Critical Risk Students')).toBeInTheDocument();
    expect(screen.getByText('High Risk Students')).toBeInTheDocument();

    // 6. Click Elective Demand tab
    const demandTab = screen.getByRole('tab', { name: /Elective Demand/i });
    fireEvent.click(demandTab);

    expect(await screen.findByText('AI401')).toBeInTheDocument();
    expect(screen.getByText('-20 Seats')).toBeInTheDocument();
  });

  it('triggers CSV export when clicking Export CSV button', async () => {
    const windowSpy = vi.spyOn(window, 'open').mockImplementation(() => null);

    render(<AnalyticsDashboardPage />);

    const exportBtn = await screen.findByRole('button', { name: /Export CSV/i });
    fireEvent.click(exportBtn);

    expect(windowSpy).toHaveBeenCalledWith(
      '/api/analytics/programme-progress/?format=csv',
      '_blank',
    );
  });

  it('blocks student role access and displays access restriction message', async () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      user: {
        id: '2',
        username: 'student_user',
        email: 'stu@univ.edu',
        first_name: 'Student',
        last_name: 'User',
        preferred_name: '',
        phone_number: '',
        memberships: [],
        is_staff: false,
        is_superuser: false,
      },
      activeMembership: null,
      activeRole: 'STUDENT',
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
      switchMembership: vi.fn(),
      hasRole: () => false,
      refreshUser: vi.fn(),
    });

    render(<AnalyticsDashboardPage />);

    expect(await screen.findByText('Access Restricted')).toBeInTheDocument();
    expect(
      screen.getByText(/Student accounts are not authorized to view aggregated institutional analytics/i),
    ).toBeInTheDocument();
  });

  it('handles report loading error with retry button', async () => {
    vi.spyOn(analyticsApi, 'getProgrammeProgress').mockRejectedValue(new Error('Network error'));

    render(<AnalyticsDashboardPage />);

    expect(
      await screen.findByText(/Failed to load progress report data. Please retry./i),
    ).toBeInTheDocument();

    // Click retry
    vi.spyOn(analyticsApi, 'getProgrammeProgress').mockResolvedValue(mockProgrammeProgress);
    const retryBtn = screen.getByRole('button', { name: /Retry Request/i });
    fireEvent.click(retryBtn);

    expect(await screen.findByText('CS-BS')).toBeInTheDocument();
  });
});
