import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { DashboardPage } from '../DashboardPage';
import { academicRecordsApi } from '../../api/academicRecords';
import { advisingApi } from '../../api/advising';
import { curriculumApi } from '../../api/curriculum';
import { analyticsApi } from '../../api/analytics';
import * as authContext from '../../context/AuthContext';

describe('DashboardPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders student dashboard with 10-point scale CGPA, progress, and actions', async () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      user: {
        id: 'u-alex',
        username: 'student_alex',
        email: 'alex.rivera@msu.edu',
        first_name: 'Alex',
        last_name: 'Rivera',
        preferred_name: 'Alex',
        phone_number: '',
        memberships: [],
        is_staff: false,
        is_superuser: false,
      },
      activeMembership: {
        id: 'm-1',
        institution_id: 'inst-1',
        institution_name: 'Metropolitan State University',
        institution_code: 'MSU',
        role: 'STUDENT',
        is_active: true,
      },
      activeRole: 'STUDENT',
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
      switchMembership: vi.fn(),
      hasRole: vi.fn(),
      refreshUser: vi.fn(),
    });

    vi.spyOn(academicRecordsApi, 'getStudentRecords').mockResolvedValue([
      {
        id: 'rec-alex',
        institution: 'inst-1',
        student: 'u-alex',
        student_username: 'student_alex',
        student_first_name: 'Alex',
        student_last_name: 'Rivera',
        student_email: 'alex.rivera@msu.edu',
        programme: 'p-1',
        programme_code: 'CS-BS',
        programme_name: 'B.S. in Computer Science',
        pinned_curriculum: 'cv-1',
        curriculum_version_number: 1,
        enrollment_term: 't-1',
        enrollment_term_code: 'FA2024',
        status: 'ACTIVE',
        repeated_course_policy: 'BEST_GRADE',
        cached_cgpa: '8.39',
        cached_total_credits: '78.00',
        created_at: '2024-09-01T00:00:00Z',
        updated_at: '2024-09-01T00:00:00Z',
      },
    ]);

    vi.spyOn(academicRecordsApi, 'getStudentRecordAudit').mockResolvedValue({
      student_id: 'rec-alex',
      student_username: 'student_alex',
      programme_code: 'CS-BS',
      programme_name: 'B.S. in Computer Science',
      version_number: 1,
      academic_year: '2024-2025',
      total_credits_required: 120,
      total_credits_earned: 78,
      total_credits_in_progress: 14,
      remaining_credits_required: 42,
      overall_cgpa: 8.39,
      min_cgpa_required: 5.0,
      is_credits_satisfied: false,
      is_cgpa_satisfied: true,
      is_degree_satisfied: false,
      groups: [],
    });

    vi.spyOn(academicRecordsApi, 'getStudentRecordTranscript').mockResolvedValue([
      {
        id: 'te-1',
        institution: 'inst-1',
        student_record: 'rec-alex',
        course: 'c-101',
        course_code: 'CS-101',
        course_title: 'Intro to Computer Science',
        term: 't-1',
        term_code: 'FA2024',
        grade: 'A',
        grade_points: 9.0,
        credits_attempted: 4,
        credits_earned: 4,
        status: 'COMPLETED',
        verification_status: 'VERIFIED',
        attempt_number: 1,
        created_at: '2024-09-01T00:00:00Z',
        updated_at: '2024-09-01T00:00:00Z',
      },
    ]);

    render(
      <BrowserRouter>
        <DashboardPage />
      </BrowserRouter>
    );

    // Verify 10-point scale display
    expect(await screen.findByText(/Welcome back, Alex/i)).toBeInTheDocument();
    expect(screen.getByText(/8.39/i)).toBeInTheDocument();
    expect(screen.getByText(/\/ 10.00 Scale/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Dr. Alice Chen/i).length).toBeGreaterThanOrEqual(1);

    // Verify Action Hub
    expect(screen.getByText(/Multi-Semester Planner/i)).toBeInTheDocument();
    expect(screen.getByText(/Official Degree Audit/i)).toBeInTheDocument();
    expect(screen.getByText(/Career Guidance/i)).toBeInTheDocument();

    // Verify no debug artifacts
    expect(screen.queryByText(/Phase 01 Shell Preview/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Verify API Health/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Engine Connected/i)).not.toBeInTheDocument();
  });

  it('renders advisor dashboard with review queue and advisee roster', async () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      user: {
        id: 'u-alice',
        username: 'advisor_alice',
        email: 'alice.chen@msu.edu',
        first_name: 'Alice',
        last_name: 'Chen',
        preferred_name: 'Dr. Alice Chen',
        phone_number: '',
        memberships: [],
        is_staff: false,
        is_superuser: false,
      },
      activeMembership: {
        id: 'm-2',
        institution_id: 'inst-1',
        institution_name: 'Metropolitan State University',
        institution_code: 'MSU',
        role: 'ADVISOR',
        is_active: true,
      },
      activeRole: 'ADVISOR',
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
      switchMembership: vi.fn(),
      hasRole: vi.fn(),
      refreshUser: vi.fn(),
    });

    vi.spyOn(advisingApi, 'fetchQueue').mockResolvedValue([
      {
        plan_id: 'plan-1',
        plan_name: "Alex's Degree Plan",
        status: 'SUBMITTED',
        row_version: 1,
        student_id: 'rec-alex',
        student_username: 'student_alex',
        student_email: 'alex@msu.edu',
        programme_code: 'CS-BS',
        programme_name: 'B.S. in Computer Science',
        latest_version_id: 'pv-1',
        latest_version_number: 1,
        latest_version_status: 'SUBMITTED',
        submitted_at: '2026-11-15T00:00:00Z',
        waiting_days: 1,
        override_count: 0,
        hard_constraints_count: 0,
        warnings_count: 0,
        is_valid_for_submission: true,
        projected_graduation_term: 'SP2027',
      },
    ]);

    vi.spyOn(academicRecordsApi, 'getStudentRecords').mockResolvedValue([]);

    render(
      <BrowserRouter>
        <DashboardPage />
      </BrowserRouter>
    );

    expect(await screen.findByText(/Advisor Academic Operations/i)).toBeInTheDocument();
    expect(screen.getByText(/Pending Plan Reviews/i)).toBeInTheDocument();
    expect(screen.getAllByText(/10.0 Scale/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Priority Plan Review Queue/i)).toBeInTheDocument();
    expect(screen.getByText("Alex's Degree Plan")).toBeInTheDocument();
  });

  it('renders coordinator dashboard with programmes catalog overview', async () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      user: {
        id: 'u-cora',
        username: 'coordinator_cora',
        email: 'cora@msu.edu',
        first_name: 'Cora',
        last_name: 'Vance',
        preferred_name: 'Cora Vance',
        phone_number: '',
        memberships: [],
        is_staff: false,
        is_superuser: false,
      },
      activeMembership: {
        id: 'm-3',
        institution_id: 'inst-1',
        institution_name: 'Metropolitan State University',
        institution_code: 'MSU',
        role: 'COORDINATOR',
        is_active: true,
      },
      activeRole: 'COORDINATOR',
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
      switchMembership: vi.fn(),
      hasRole: vi.fn(),
      refreshUser: vi.fn(),
    });

    vi.spyOn(curriculumApi, 'getProgrammes').mockResolvedValue([
      {
        id: 'p-1',
        code: 'CS-BS',
        name: 'B.S. in Computer Science',
        degree_type: 'BACHELOR',
        department: 'Computer Science',
        description: 'Undergraduate CS curriculum.',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
      },
    ]);
    vi.spyOn(curriculumApi, 'getCourses').mockResolvedValue([]);

    render(
      <BrowserRouter>
        <DashboardPage />
      </BrowserRouter>
    );

    expect(await screen.findByText(/Programme Coordinator Operations/i)).toBeInTheDocument();
    expect(screen.getByText(/Curriculum Authoring/i)).toBeInTheDocument();
    expect(screen.getByText(/Deterministic DAG/i)).toBeInTheDocument();
    expect(screen.getByText(/Academic Degree Programmes/i)).toBeInTheDocument();
  });

  it('renders Head of Department (HOD) dashboard with department metrics', async () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      user: {
        id: 'u-alan',
        username: 'hod_alan',
        email: 'alan.sterling@msu.edu',
        first_name: 'Alan',
        last_name: 'Sterling',
        preferred_name: 'Dr. Alan Sterling',
        phone_number: '',
        memberships: [],
        is_staff: false,
        is_superuser: false,
      },
      activeMembership: {
        id: 'm-4',
        institution_id: 'inst-1',
        institution_name: 'Metropolitan State University',
        institution_code: 'MSU',
        role: 'HOD',
        is_active: true,
      },
      activeRole: 'HOD',
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
      switchMembership: vi.fn(),
      hasRole: vi.fn(),
      refreshUser: vi.fn(),
    });

    vi.spyOn(analyticsApi, 'getOverview').mockResolvedValue({
      total_active_students: 185,
      total_plans: 140,
      plans_pending_review: 6,
      critical_or_high_risk_students: 3,
      top_bottlenecks: [
        {
          course_code: 'MATH-151',
          course_name: 'Calculus I',
          impacted_students_count: 14,
        },
      ],
    });

    vi.spyOn(analyticsApi, 'getProgrammeProgress').mockResolvedValue({
      report: 'programme_progress',
      generated_at: '2026-11-16T00:00:00Z',
      total_programmes: 1,
      items: [
        {
          programme_id: 'p-1',
          programme_code: 'CS-BS',
          programme_name: 'B.S. in Computer Science',
          min_credits_required: 120,
          total_students: 120,
          avg_cgpa: 8.65,
          avg_earned_credits: 74,
          bracket_0_25: 10,
          bracket_26_50: 25,
          bracket_51_75: 45,
          bracket_76_100: 40,
          near_completion: 22,
        },
      ],
    });

    render(
      <BrowserRouter>
        <DashboardPage />
      </BrowserRouter>
    );

    expect(await screen.findByText(/Department Executive Overview/i)).toBeInTheDocument();
    expect(screen.getByText('185')).toBeInTheDocument();
    expect(screen.getByText(/Department Avg CGPA/i)).toBeInTheDocument();
    expect(screen.getByText(/Curriculum Bottlenecks/i)).toBeInTheDocument();
    expect(screen.getByText(/MATH-151/i)).toBeInTheDocument();
  });
});
