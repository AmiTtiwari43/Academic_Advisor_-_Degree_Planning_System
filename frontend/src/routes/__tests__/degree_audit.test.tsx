import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { DegreeAuditPage } from '../DegreeAuditPage';
import {
  academicRecordsApi,
  StudentRecord,
  StudentRecordDetail,
  DegreeAuditReport,
  CourseEligibilityResult,
} from '../../api/academicRecords';

const mockStudentRecords: StudentRecord[] = [
  {
    id: 'rec-1',
    institution: 'inst-1',
    student: 'user-bob',
    student_username: 'student_bob',
    student_first_name: 'Bob',
    student_last_name: 'Smith',
    student_email: 'bob@audit.edu',
    programme: 'prog-1',
    programme_code: 'BS_CS',
    programme_name: 'B.S. in Computer Science',
    pinned_curriculum: 'cur-1',
    curriculum_version_number: 1,
    enrollment_term: 'term-1',
    enrollment_term_code: 'FA2026',
    expected_graduation_term: null,
    repeated_course_policy: 'BEST_GRADE',
    status: 'ACTIVE',
    cached_cgpa: '3.50',
    cached_total_credits: '16.00',
    created_at: '2026-09-01T00:00:00Z',
    updated_at: '2026-09-01T00:00:00Z',
  },
];

const mockStudentRecordDetail: StudentRecordDetail = {
  ...mockStudentRecords[0],
  transcript_entries: [
    {
      id: 'te-1',
      institution: 'inst-1',
      student_record: 'rec-1',
      course: 'c-101',
      course_code: 'CS101',
      course_title: 'Intro to Computer Science',
      term: 'term-1',
      term_code: 'FA2026',
      grade: 'A',
      credits_attempted: 4,
      credits_earned: 4,
      status: 'COMPLETED',
      verification_status: 'VERIFIED',
      attempt_number: 1,
      created_at: '2026-09-01T00:00:00Z',
      updated_at: '2026-09-01T00:00:00Z',
    },
    {
      id: 'te-2',
      institution: 'inst-1',
      student_record: 'rec-1',
      course: 'c-102',
      course_code: 'CS102',
      course_title: 'Data Structures',
      term: 'term-1',
      term_code: 'FA2026',
      grade: 'B',
      credits_attempted: 4,
      credits_earned: 4,
      status: 'COMPLETED',
      verification_status: 'VERIFIED',
      attempt_number: 1,
      created_at: '2026-09-01T00:00:00Z',
      updated_at: '2026-09-01T00:00:00Z',
    },
  ],
  transfer_credits: [
    {
      id: 'tc-1',
      institution: 'inst-1',
      student_record: 'rec-1',
      course_code: 'MATH101',
      course_title: 'Calculus I',
      source_institution: 'State College',
      credits: 4,
      grade: 'A',
      is_verified: true,
      verified_at: '2026-08-01T00:00:00Z',
      created_at: '2026-08-01T00:00:00Z',
      updated_at: '2026-08-01T00:00:00Z',
    },
  ],
  exemptions: [
    {
      id: 'ex-1',
      institution: 'inst-1',
      student_record: 'rec-1',
      course: 'c-gen',
      course_code: 'GEN101',
      course_title: 'Writing',
      reason: 'AP English credit waiver',
      approved_by: 'adv-1',
      approved_by_username: 'advisor_carol',
      approved_at: '2026-08-15T00:00:00Z',
      created_at: '2026-08-15T00:00:00Z',
      updated_at: '2026-08-15T00:00:00Z',
    },
  ],
};

const mockAuditReport: DegreeAuditReport = {
  student_id: 'rec-1',
  student_username: 'student_bob',
  programme_code: 'BS_CS',
  programme_name: 'B.S. in Computer Science',
  version_number: 1,
  academic_year: '2026-2027',
  total_credits_required: 20,
  total_credits_earned: 16,
  total_credits_in_progress: 4,
  remaining_credits_required: 4,
  overall_cgpa: 3.5,
  min_cgpa_required: 2.0,
  is_credits_satisfied: false,
  is_cgpa_satisfied: true,
  is_degree_satisfied: false,
  groups: [
    {
      group_id: 'grp-core',
      name: 'Major Core',
      group_type: 'MANDATORY',
      min_credits: 8,
      min_courses: 2,
      min_cgpa: null,
      earned_credits: 8,
      in_progress_credits: 0,
      remaining_credits: 0,
      is_satisfied: true,
      cgpa_satisfied: true,
      allocated_courses: [
        {
          course_id: 'c-101',
          course_code: 'CS101',
          course_title: 'Intro to Computer Science',
          grade: 'A',
          earned_credits: 4,
          source: 'TRANSCRIPT',
          attempt_number: 1,
        },
        {
          course_id: 'c-102',
          course_code: 'CS102',
          course_title: 'Data Structures',
          grade: 'B',
          earned_credits: 4,
          source: 'TRANSCRIPT',
          attempt_number: 1,
        },
      ],
      remaining_mandatory_courses: [],
      in_progress_courses: [],
    },
    {
      group_id: 'grp-math',
      name: 'Math Requirements',
      group_type: 'MANDATORY',
      min_credits: 8,
      min_courses: 2,
      min_cgpa: 2.5,
      earned_credits: 4,
      in_progress_credits: 0,
      remaining_credits: 4,
      is_satisfied: false,
      cgpa_satisfied: true,
      allocated_courses: [
        {
          course_id: 'c-m101',
          course_code: 'MATH101',
          course_title: 'Calculus I',
          grade: 'A',
          earned_credits: 4,
          source: 'TRANSFER',
        },
      ],
      remaining_mandatory_courses: [
        {
          course_id: 'c-m102',
          course_code: 'MATH102',
          course_title: 'Calculus II',
          credits: 4,
        },
      ],
      in_progress_courses: [],
    },
  ],
};

const mockEligibilitySatisfied: CourseEligibilityResult = {
  course_id: 'c-m102',
  course_code: 'MATH102',
  course_title: 'Calculus II',
  eligible: true,
  status: 'SATISFIED',
  is_satisfied: true,
  is_indeterminate: false,
  blocking_reasons: [],
  execution_tree: { type: 'course_completed', status: 'SATISFIED' },
};

describe('DegreeAuditPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(academicRecordsApi, 'getStudentRecords').mockResolvedValue(mockStudentRecords);
    vi.spyOn(academicRecordsApi, 'getStudentRecord').mockResolvedValue(mockStudentRecordDetail);
    vi.spyOn(academicRecordsApi, 'getStudentRecordAudit').mockResolvedValue(mockAuditReport);
    vi.spyOn(academicRecordsApi, 'checkCourseEligibility').mockResolvedValue(mockEligibilitySatisfied);
  });

  const renderComponent = () =>
    render(
      <BrowserRouter>
        <DegreeAuditPage />
      </BrowserRouter>
    );

  it('renders student metadata and degree audit progress card', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByTestId('student-meta-banner')).toBeInTheDocument();
    });

    expect(screen.getByText('Bob Smith')).toBeInTheDocument();
    expect(screen.getByText(/B\.S\. in Computer Science \(BS_CS\)/)).toBeInTheDocument();
    expect(screen.getByText(/Pinned Curriculum: v1/)).toBeInTheDocument();
    expect(screen.getByText(/Repeats: BEST_GRADE/)).toBeInTheDocument();

    // Progress bar metrics
    expect(screen.getByTestId('audit-earned-credits')).toHaveTextContent('16');
    expect(screen.getByText('/ 20 Credits Required')).toBeInTheDocument();
    expect(screen.getByTestId('audit-inprogress-credits')).toHaveTextContent('+4 in progress');
    expect(screen.getByTestId('audit-cgpa')).toHaveTextContent('3.50');
    expect(screen.getByTestId('audit-overall-status')).toHaveTextContent('4 CREDITS REMAINING');
  });

  it('renders curriculum requirement groups with satisfaction status', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByTestId('requirement-group-grp-core')).toBeInTheDocument();
    });

    // Major Core group is satisfied
    expect(screen.getByTestId('group-status-grp-core')).toHaveTextContent('Satisfied');
    expect(screen.getByTestId('group-earned-grp-core')).toHaveTextContent('8');

    // Math Requirements group is unsatisfied
    expect(screen.getByTestId('group-status-grp-math')).toHaveTextContent('4 cr needed');
    expect(screen.getByTestId('remaining-course-MATH102')).toBeInTheDocument();
  });

  it('opens prerequisite eligibility check modal for remaining courses', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByTestId('check-eligibility-btn-MATH102')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('check-eligibility-btn-MATH102'));

    await waitFor(() => {
      expect(screen.getByTestId('course-eligibility-modal')).toBeInTheDocument();
    });

    expect(academicRecordsApi.checkCourseEligibility).toHaveBeenCalledWith('rec-1', 'c-m102');

    await waitFor(() => {
      expect(screen.getByTestId('eligibility-verdict')).toHaveTextContent('Prerequisites Satisfied');
    });

    // Close modal
    fireEvent.click(screen.getByTestId('close-eligibility-modal'));
    await waitFor(() => {
      expect(screen.queryByTestId('course-eligibility-modal')).not.toBeInTheDocument();
    });
  });

  it('switches between Degree Audit and Official Transcript history tabs', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByTestId('tab-transcript-history')).toBeInTheDocument();
    });

    // Click transcript tab
    fireEvent.click(screen.getByTestId('tab-transcript-history'));

    await waitFor(() => {
      expect(screen.getByTestId('transcript-table-view')).toBeInTheDocument();
    });

    // Transcript entries rendered
    expect(screen.getByText('Intro to Computer Science')).toBeInTheDocument();
    expect(screen.getByText('Data Structures')).toBeInTheDocument();
    expect(screen.getByText('State College')).toBeInTheDocument();
    expect(screen.getByText('AP English credit waiver')).toBeInTheDocument();

    // Switch back to audit
    fireEvent.click(screen.getByTestId('tab-degree-audit'));
    await waitFor(() => {
      expect(screen.getByTestId('degree-audit-progress-card')).toBeInTheDocument();
    });
  });

  it('handles error state properly and provides retry option', async () => {
    vi.spyOn(academicRecordsApi, 'getStudentRecordAudit').mockRejectedValueOnce(
      new Error('Engine timeout')
    );

    renderComponent();

    await waitFor(() => {
      expect(screen.getByTestId('audit-error-state')).toBeInTheDocument();
    });

    expect(screen.getByText(/Engine timeout/)).toBeInTheDocument();
  });
});
