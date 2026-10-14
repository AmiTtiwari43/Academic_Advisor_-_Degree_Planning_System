import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { DegreePlannerPage } from '../DegreePlannerPage';
import {
  academicRecordsApi,
  StudentRecord,
  AcademicTerm,
} from '../../api/academicRecords';
import { Course, curriculumApi, Programme } from '../../api/curriculum';
import {
  Plan,
  PlanSimulationReport,
  planningApi,
} from '../../api/planning';

const mockStudentRecord: StudentRecord = {
  id: 'rec-1',
  institution: 'inst-1',
  student: 'user-alice',
  student_username: 'student_alice',
  student_first_name: 'Alice',
  student_last_name: 'Walker',
  student_email: 'alice@plan.edu',
  programme: 'prog-1',
  programme_code: 'BS_CS',
  programme_name: 'B.S. Computer Science',
  pinned_curriculum: 'cur-1',
  curriculum_version_number: 1,
  enrollment_term: 'term-1',
  enrollment_term_code: 'FA2026',
  expected_graduation_term: null,
  repeated_course_policy: 'BEST_GRADE',
  status: 'ACTIVE',
  cached_cgpa: '3.80',
  cached_total_credits: '0.00',
  created_at: '2026-09-01T00:00:00Z',
  updated_at: '2026-09-01T00:00:00Z',
};

const mockTerms: AcademicTerm[] = [
  {
    id: 'term-1',
    institution: 'inst-1',
    code: 'FA2026',
    name: 'Fall 2026',
    season: 'FALL',
    year: 2026,
    start_date: '2026-09-01',
    end_date: '2026-12-15',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'term-2',
    institution: 'inst-1',
    code: 'SP2027',
    name: 'Spring 2027',
    season: 'SPRING',
    year: 2027,
    start_date: '2027-01-15',
    end_date: '2027-05-15',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
];

const mockCourses: Course[] = [
  {
    id: 'c-101',
    code: 'CS101',
    title: 'Intro to CS',
    description: 'Foundations of computer science',
    credits: 4,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'c-102',
    code: 'CS102',
    title: 'Data Structures',
    description: 'Data structures & algorithms',
    credits: 4,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
  },
];

const mockPlan: Plan = {
  id: 'plan-1',
  institution: 'inst-1',
  student_record: 'rec-1',
  student_username: 'student_alice',
  curriculum_version: 'cur-1',
  curriculum_version_number: 1,
  programme_name: 'B.S. Computer Science',
  name: 'Primary 4-Year Plan',
  is_primary: true,
  status: 'DRAFT',
  row_version: 1,
  items: [
    {
      id: 'item-1',
      plan: 'plan-1',
      course: 'c-101',
      course_code: 'CS101',
      course_title: 'Intro to CS',
      course_credits: 4,
      planned_term: 'term-1',
      planned_term_code: 'FA2026',
      term_index: 1,
      position: 1,
    },
  ],
  created_at: '2026-09-01T00:00:00Z',
  updated_at: '2026-09-01T00:00:00Z',
};

const mockSimulationValid: PlanSimulationReport = {
  plan_id: 'plan-1',
  plan_name: 'Primary 4-Year Plan',
  student_username: 'student_alice',
  curriculum_version_number: 1,
  total_planned_credits: '4.00',
  total_cumulative_credits: '4.00',
  is_valid_for_submission: true,
  hard_constraints: [],
  warnings: [
    {
      code: 'TERM_CREDIT_UNDERLOAD',
      severity: 'WARNING',
      message: 'Term 1 (FA2026) is below full-time minimum of 12 credits.',
      term_code: 'FA2026',
      term_index: 1,
    },
  ],
  projected_graduation_term: 'SP2027',
  graduation_projection_reason: 'All degree requirements satisfied by Spring 2027.',
  audit_report: {
    total_credits_required: '16.00',
    total_credits_earned: '4.00',
    groups: [],
  },
  terms: [
    {
      term_id: 'term-1',
      term_code: 'FA2026',
      term_name: 'Fall 2026',
      term_index: 1,
      total_credits: 4,
      is_credit_limit_exceeded: false,
      is_credit_minimum_met: false,
      courses: [
        {
          course_id: 'c-101',
          course_code: 'CS101',
          course_title: 'Intro to CS',
          credits: 4,
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
};

const mockSimulationBlocked: PlanSimulationReport = {
  ...mockSimulationValid,
  is_valid_for_submission: false,
  hard_constraints: [
    {
      code: 'PREREQUISITE_UNSATISFIED',
      severity: 'HARD',
      message: 'Prerequisite for CS102 unsatisfied prior to Term 1: Must complete CS101 with C.',
      course_code: 'CS102',
      term_code: 'FA2026',
      term_index: 1,
    },
  ],
};

const mockProgrammes: Programme[] = [
  {
    id: 'prog-2',
    code: 'BS_DS',
    name: 'B.S. Data Science',
    degree_type: 'BACHELOR',
    department: 'CS',
    description: 'Data Science programme',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    curriculum_versions: [
      {
        id: 'ver-ds-1',
        version_number: 1,
        academic_year: '2026-2027',
        status: 'PUBLISHED',
        total_credits_required: 120,
        min_cgpa_required: 2.5,
        is_editable: false,
        created_at: '2026-01-01T00:00:00Z',
      },
    ],
  },
];

describe('DegreePlannerPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.spyOn(academicRecordsApi, 'getStudentRecords').mockResolvedValue([mockStudentRecord]);
    vi.spyOn(academicRecordsApi, 'getAcademicTerms').mockResolvedValue(mockTerms);
    vi.spyOn(curriculumApi, 'getCourses').mockResolvedValue(mockCourses);
    vi.spyOn(curriculumApi, 'getProgrammes').mockResolvedValue(mockProgrammes);

    vi.spyOn(planningApi, 'fetchPlans').mockResolvedValue([mockPlan]);
    vi.spyOn(planningApi, 'fetchPlan').mockResolvedValue(mockPlan);
    vi.spyOn(planningApi, 'simulatePlan').mockResolvedValue(mockSimulationValid);
    vi.spyOn(planningApi, 'addCourseToPlan').mockResolvedValue({
      id: 'item-2',
      plan: 'plan-1',
      course: 'c-102',
      course_code: 'CS102',
      course_title: 'Data Structures',
      course_credits: 4,
      planned_term: 'term-2',
      planned_term_code: 'SP2027',
      term_index: 2,
      position: 1,
    });
    vi.spyOn(planningApi, 'removeCourseFromPlan').mockResolvedValue({ status: 'removed' });
    vi.spyOn(planningApi, 'moveCourseInPlan').mockResolvedValue({
      id: 'item-1',
      plan: 'plan-1',
      course: 'c-101',
      course_code: 'CS101',
      course_title: 'Intro to CS',
      course_credits: 4,
      planned_term: 'term-2',
      planned_term_code: 'SP2027',
      term_index: 2,
      position: 1,
    });
    vi.spyOn(planningApi, 'submitPlan').mockResolvedValue({
      id: 'ver-snap-1',
      institution: 'inst-1',
      plan: 'plan-1',
      version_number: 1,
      snapshot_data: {
        plan_id: 'plan-1',
        plan_name: 'Primary 4-Year Plan',
        curriculum_version_id: 'cur-1',
        curriculum_version_number: 1,
        items: [],
        simulation: mockSimulationValid,
        submitted_by_username: 'student_alice',
        submission_note: 'Ready for review',
      },
      status: 'SUBMITTED',
      submitted_at: '2026-10-14T20:00:00Z',
    });
    vi.spyOn(planningApi, 'fetchPlanVersions').mockResolvedValue([
      {
        id: 'ver-snap-1',
        institution: 'inst-1',
        plan: 'plan-1',
        version_number: 1,
        snapshot_data: {
          plan_id: 'plan-1',
          plan_name: 'Primary 4-Year Plan',
          curriculum_version_id: 'cur-1',
          curriculum_version_number: 1,
          items: [],
          simulation: mockSimulationValid,
          submitted_by_username: 'student_alice',
          submission_note: '',
        },
        status: 'SUBMITTED',
        submitted_at: '2026-10-14T20:00:00Z',
      },
    ]);
    vi.spyOn(planningApi, 'comparePlanVersions').mockResolvedValue({
      version_a: 1,
      version_b: 1,
      items_added: [],
      items_removed: [],
      items_moved: [],
      simulation_a: mockSimulationValid,
      simulation_b: mockSimulationValid,
    });
    vi.spyOn(planningApi, 'simulateWhatIf').mockResolvedValue({
      ...mockSimulationValid,
      curriculum_version_number: 1,
      projected_graduation_term: 'FA2028',
      graduation_projection_reason: 'What-If Simulation for Data Science completes by FA2028.',
    });
  });

  const renderComponent = () =>
    render(
      <BrowserRouter>
        <DegreePlannerPage />
      </BrowserRouter>
    );

  it('renders the planner workspace with terms, planned courses, and catalog drawer', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByTestId('plan-select')).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByTestId('projected-grad-badge')).toHaveTextContent(
        'Projected Graduation: SP2027'
      );
    });

    expect(screen.getByText('Academic Degree Planner')).toBeInTheDocument();
    expect(screen.getByTestId('semester-column-grid')).toBeInTheDocument();
    expect(screen.getByTestId('course-catalog-drawer')).toBeInTheDocument();
    expect(screen.getByTestId('plan-item-CS101')).toBeInTheDocument();
  });

  it('adds a course from catalog drawer using accessible term selector', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByTestId('catalog-card-CS102')).toBeInTheDocument();
    });

    const termSelect = screen.getByTestId('select-term-CS102');
    fireEvent.change(termSelect, { target: { value: 'term-2' } });

    const addBtn = screen.getByTestId('add-btn-CS102');
    fireEvent.click(addBtn);

    await waitFor(() => {
      expect(planningApi.addCourseToPlan).toHaveBeenCalledWith('plan-1', {
        course: 'c-102',
        planned_term: 'term-2',
        term_index: 2,
      });
    });
  });

  it('moves a course between semesters using accessible keyboard dropdown', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByTestId('plan-item-CS101')).toBeInTheDocument();
    });

    const moveSelect = screen.getByLabelText('Move CS101 to another term');
    fireEvent.change(moveSelect, { target: { value: 'term-2' } });

    await waitFor(() => {
      expect(planningApi.moveCourseInPlan).toHaveBeenCalledWith('plan-1', 'item-1', {
        target_term: 'term-2',
        target_term_index: 2,
      });
    });
  });

  it('removes a course from a planned term', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByLabelText('Remove CS101 from Fall 2026')).toBeInTheDocument();
    });

    const removeBtn = screen.getByLabelText('Remove CS101 from Fall 2026');
    fireEvent.click(removeBtn);

    await waitFor(() => {
      expect(planningApi.removeCourseFromPlan).toHaveBeenCalledWith('plan-1', 'item-1');
    });
  });

  it('displays hard constraints and disables submission when plan is blocked', async () => {
    vi.spyOn(planningApi, 'simulatePlan').mockResolvedValue(mockSimulationBlocked);
    renderComponent();

    await waitFor(() => {
      expect(screen.getByTestId('hard-constraints-banner')).toBeInTheDocument();
    });

    expect(screen.getByTestId('hard-constraint-item')).toHaveTextContent(
      'Prerequisite for CS102 unsatisfied prior to Term 1'
    );

    const submitBtn = screen.getByTestId('submit-plan-btn');
    expect(submitBtn).toBeDisabled();
  });

  it('submits plan snapshot for advisor review when valid', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByTestId('submit-plan-btn')).toBeEnabled();
    });

    fireEvent.click(screen.getByTestId('submit-plan-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('submit-plan-dialog')).toBeInTheDocument();
    });

    const noteInput = screen.getByTestId('submission-note-input');
    fireEvent.change(noteInput, { target: { value: 'Please review my 4-year schedule.' } });

    const confirmBtn = screen.getByTestId('confirm-submit-plan-btn');
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(planningApi.submitPlan).toHaveBeenCalledWith('plan-1', 'Please review my 4-year schedule.');
    });
  });

  it('opens What-If modal and runs isolated simulation without record mutations', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByTestId('what-if-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('what-if-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('what-if-modal')).toBeInTheDocument();
    });

    expect(screen.getByTestId('what-if-disclaimer')).toHaveTextContent(
      'Simulation Mode: This analysis simulates degree requirements against an alternative curriculum version'
    );

    const runBtn = screen.getByTestId('run-what-if-btn');
    fireEvent.click(runBtn);

    await waitFor(() => {
      expect(planningApi.simulateWhatIf).toHaveBeenCalledWith({
        student_record_id: 'rec-1',
        target_curriculum_version_id: 'ver-ds-1',
        plan_id: 'plan-1',
      });
    });

    await waitFor(() => {
      expect(screen.getByTestId('what-if-grad-term')).toHaveTextContent('FA2028');
    });
  });

  it('opens snapshot version diff modal and displays version history', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByTestId('version-history-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('version-history-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('plan-version-diff-modal')).toBeInTheDocument();
    });

    expect(screen.getByTestId('snapshots-history-table')).toBeInTheDocument();
  });

  it('handles optimistic concurrency conflict (409) with auto-reload alert', async () => {
    const error409 = { status: 409, message: 'Plan row_version conflict' };
    vi.spyOn(planningApi, 'addCourseToPlan').mockRejectedValue(error409);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByTestId('add-btn-CS102')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('add-btn-CS102'));

    await waitFor(() => {
      expect(screen.getByTestId('concurrency-conflict-alert')).toBeInTheDocument();
    });

    expect(screen.getByTestId('concurrency-conflict-alert')).toHaveTextContent(
      'Conflict: This plan was modified in another session. Reloading latest plan...'
    );
  });
});
