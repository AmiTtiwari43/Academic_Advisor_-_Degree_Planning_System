import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { AdvisorWorkspacePage } from '../AdvisorWorkspacePage';
import { advisingApi, ReviewQueueItem, PlanAuditLog } from '../../api/advising';
import { planningApi, Plan, PlanVersion } from '../../api/planning';

const mockQueueItem: ReviewQueueItem = {
  plan_id: 'plan-1',
  plan_name: 'Graduation Plan 2026',
  status: 'SUBMITTED',
  row_version: 1,
  student_id: 'rec-1',
  student_username: 'student_alex',
  student_email: 'alex@advising.edu',
  programme_code: 'SE',
  programme_name: 'Software Engineering',
  latest_version_id: 'ver-1',
  latest_version_number: 1,
  latest_version_status: 'SUBMITTED',
  submitted_at: '2026-10-10T12:00:00Z',
  waiting_days: 4,
  override_count: 0,
  hard_constraints_count: 0,
  warnings_count: 1,
  is_valid_for_submission: true,
  projected_graduation_term: 'SP2028',
};

const mockPlan: Plan = {
  id: 'plan-1',
  institution: 'inst-1',
  student_record: 'rec-1',
  student_username: 'student_alex',
  curriculum_version: 'curr-1',
  curriculum_version_number: 1,
  programme_name: 'Software Engineering',
  name: 'Graduation Plan 2026',
  is_primary: true,
  status: 'SUBMITTED',
  row_version: 1,
  items: [
    {
      id: 'item-1',
      plan: 'plan-1',
      course: 'c-101',
      course_code: 'CS101',
      course_title: 'Intro to CS',
      course_credits: '4.00',
      planned_term: 'term-1',
      planned_term_code: 'FA2026',
      term_index: 1,
      position: 0,
    },
  ],
  created_at: '2026-10-10T00:00:00Z',
  updated_at: '2026-10-10T12:00:00Z',
};

const mockVersions: PlanVersion[] = [
  {
    id: 'ver-1',
    institution: 'inst-1',
    plan: 'plan-1',
    version_number: 1,
    status: 'SUBMITTED',
    snapshot_data: {
      plan_id: 'plan-1',
      plan_name: 'Graduation Plan 2026',
      curriculum_version_id: 'curr-1',
      curriculum_version_number: 1,
      items: [
        {
          course_id: 'c-101',
          course_code: 'CS101',
          course_title: 'Intro to CS',
          credits: '4.00',
          term_id: 'term-1',
          term_code: 'FA2026',
          term_index: 1,
          position: 0,
        },
      ],
      simulation: {
        plan_id: 'plan-1',
        plan_name: 'Graduation Plan 2026',
        student_username: 'student_alex',
        curriculum_version_number: 1,
        total_planned_credits: '4.00',
        total_cumulative_credits: '4.00',
        is_valid_for_submission: true,
        hard_constraints: [],
        warnings: [
          {
            code: 'MIN_TERM_LOAD',
            severity: 'WARNING',
            message: 'Fall 2026 planned credits (4.00) below minimum recommended load (12.00).',
          },
        ],
        projected_graduation_term: 'SP2028',
        graduation_projection_reason: 'Normal progress',
        audit_report: {},
        terms: [
          {
            term_id: 'term-1',
            term_code: 'FA2026',
            term_name: 'Fall 2026',
            term_index: 1,
            total_credits: '4.00',
            is_credit_limit_exceeded: false,
            is_credit_minimum_met: false,
            courses: [
              {
                course_id: 'c-101',
                course_code: 'CS101',
                course_title: 'Intro to CS',
                credits: '4.00',
                term_index: 1,
                term_code: 'FA2026',
                is_eligible: true,
                prerequisite_satisfied: true,
                corequisite_satisfied: true,
                offering_available: true,
                blocking_reasons: [],
              },
            ],
          },
        ],
      },
      submitted_by_username: 'student_alex',
      submission_note: 'Initial review please',
    },
    submitted_at: '2026-10-10T12:00:00Z',
  },
];

const mockAuditLogs: PlanAuditLog[] = [
  {
    id: 'log-1',
    institution: 'inst-1',
    plan: 'plan-1',
    plan_version: 'ver-1',
    version_number: 1,
    actor_username: 'student_alex',
    action: 'PLAN_SUBMIT',
    from_status: 'DRAFT',
    to_status: 'SUBMITTED',
    comment: 'Initial review please',
    metadata: {},
    created_at: '2026-10-10T12:00:00Z',
  },
];

describe('AdvisorWorkspacePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(advisingApi, 'fetchQueue').mockResolvedValue([mockQueueItem]);
    vi.spyOn(planningApi, 'fetchPlan').mockResolvedValue(mockPlan);
    vi.spyOn(planningApi, 'fetchPlanVersions').mockResolvedValue(mockVersions);
    vi.spyOn(advisingApi, 'fetchAuditHistory').mockResolvedValue(mockAuditLogs);
    vi.spyOn(advisingApi, 'startReview').mockResolvedValue({
      id: 'dec-1',
      institution: 'inst-1',
      plan: 'plan-1',
      plan_version: 'ver-1',
      version_number: 1,
      reviewer: 1,
      reviewer_username: 'advisor_alice',
      action: 'START_REVIEW',
      from_status: 'SUBMITTED',
      to_status: 'UNDER_REVIEW',
      comments: 'Advisor initiated official review.',
      created_at: '2026-10-14T00:00:00Z',
    });
    vi.spyOn(advisingApi, 'approvePlan').mockResolvedValue({
      id: 'dec-2',
      institution: 'inst-1',
      plan: 'plan-1',
      plan_version: 'ver-1',
      version_number: 1,
      reviewer: 1,
      reviewer_username: 'advisor_alice',
      action: 'APPROVE',
      from_status: 'UNDER_REVIEW',
      to_status: 'APPROVED',
      comments: 'Plan verified and approved.',
      created_at: '2026-10-14T00:01:00Z',
    });
    vi.spyOn(advisingApi, 'recordOverride').mockResolvedValue({
      id: 'ov-1',
      institution: 'inst-1',
      plan: 'plan-1',
      plan_version: 'ver-1',
      version_number: 1,
      actor: 1,
      actor_username: 'advisor_alice',
      override_type: 'PREREQUISITE_OVERRIDE',
      justification: 'Approved based on relevant professional programming background.',
      metadata: {},
      created_at: '2026-10-14T00:02:00Z',
    });
  });

  it('renders advisor queue, metric cards, and initial plan detail', async () => {
    render(
      <BrowserRouter>
        <AdvisorWorkspacePage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Advisor Workspace & Degree Plan Review')).toBeInTheDocument();
      expect(screen.getByText('student_alex')).toBeInTheDocument();
      expect(screen.getByText('4 days')).toBeInTheDocument();
      expect(screen.getByText('1 Warning(s)')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /start official review/i })).toBeInTheDocument();
    });
  });

  it('triggers start official review action', async () => {
    render(
      <BrowserRouter>
        <AdvisorWorkspacePage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /start official review/i })).toBeInTheDocument();
    });

    const startBtn = screen.getByRole('button', { name: /start official review/i });
    fireEvent.click(startBtn);

    await waitFor(() => {
      expect(advisingApi.startReview).toHaveBeenCalledWith('plan-1', {
        expected_row_version: 1,
      });
    });
  });

  it('opens and validates override modal with minimum 15 characters', async () => {
    render(
      <BrowserRouter>
        <AdvisorWorkspacePage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /record override/i })).toBeInTheDocument();
    });

    // Open override modal
    fireEvent.click(screen.getByRole('button', { name: /record override/i }));
    expect(screen.getByText('Record Academic Override')).toBeInTheDocument();

    const submitBtn = screen.getByRole('button', { name: /record authoritative override/i });
    expect(submitBtn).toBeDisabled();

    // Type 10 characters (below 15)
    const textarea = screen.getByPlaceholderText(/state the verifiable academic rationale/i);
    fireEvent.change(textarea, { target: { value: 'Too short!' } });
    expect(submitBtn).toBeDisabled();

    // Type valid >= 15 characters
    fireEvent.change(textarea, {
      target: {
        value: 'Approved based on relevant professional programming background.',
      },
    });
    expect(submitBtn).not.toBeDisabled();

    // Submit override
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(advisingApi.recordOverride).toHaveBeenCalledWith('plan-1', {
        override_type: 'PREREQUISITE_OVERRIDE',
        justification: 'Approved based on relevant professional programming background.',
      });
    });
  });

  it('handles optimistic concurrency conflict (409) with error banner', async () => {
    vi.spyOn(advisingApi, 'startReview').mockRejectedValueOnce({
      response: {
        status: 409,
        data: { message: 'Plan was modified by another session (OCC conflict).' },
      },
    });

    render(
      <BrowserRouter>
        <AdvisorWorkspacePage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /start official review/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /start official review/i }));

    await waitFor(() => {
      expect(
        screen.getByText('Optimistic Concurrency Conflict (409)')
      ).toBeInTheDocument();
      expect(
        screen.getByText('Plan was modified by another session (OCC conflict).')
      ).toBeInTheDocument();
    });
  });
});
