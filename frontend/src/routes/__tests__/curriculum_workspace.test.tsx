import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { CurriculumWorkspacePage } from '../CurriculumWorkspacePage';
import { curriculumApi, Programme, CurriculumVersionDetail, Course } from '../../api/curriculum';

const mockCourses: Course[] = [
  {
    id: 'course-1',
    code: 'CS101',
    title: 'Intro to Computer Science',
    description: 'Basics of CS',
    credits: 4,
    default_credit_category_code: 'MAJOR_CORE',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'course-2',
    code: 'CS201',
    title: 'Data Structures',
    description: 'Data Structures and Algorithms',
    credits: 4,
    default_credit_category_code: 'MAJOR_CORE',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
  },
];

const mockVersionDetail: CurriculumVersionDetail = {
  id: 'ver-1',
  programme: 'prog-1',
  programme_code: 'BSCS',
  programme_name: 'B.S. in Computer Science',
  version_number: 1,
  academic_year: '2026-2027',
  status: 'DRAFT',
  total_credits_required: 120,
  min_cgpa_required: 2.0,
  is_editable: true,
  change_summary: 'Initial draft for 2026-2027',
  created_at: '2026-01-01T00:00:00Z',
  requirement_groups: [
    {
      id: 'group-1',
      curriculum_version: 'ver-1',
      name: 'Computer Science Core',
      group_type: 'MANDATORY',
      min_credits: 8,
      min_courses: 2,
      display_order: 1,
      group_courses: [
        {
          id: 'gc-1',
          requirement_group: 'group-1',
          course: 'course-1',
          course_code: 'CS101',
          course_title: 'Intro to Computer Science',
          course_credits: 4,
          is_mandatory: true,
          display_order: 1,
        },
        {
          id: 'gc-2',
          requirement_group: 'group-1',
          course: 'course-2',
          course_code: 'CS201',
          course_title: 'Data Structures',
          course_credits: 4,
          is_mandatory: true,
          display_order: 2,
        },
      ],
      created_at: '2026-01-01T00:00:00Z',
    },
  ],
  prerequisite_rules: [
    {
      id: 'rule-1',
      curriculum_version: 'ver-1',
      course: 'course-2',
      course_code: 'CS201',
      course_title: 'Data Structures',
      description: 'Requires CS101 with grade C',
      rule_json: {
        type: 'COURSE_COMPLETED',
        course_code: 'CS101',
        min_grade: 'C',
      },
      created_at: '2026-01-01T00:00:00Z',
    },
  ],
};

const mockProgrammes: Programme[] = [
  {
    id: 'prog-1',
    code: 'BSCS',
    name: 'B.S. in Computer Science',
    degree_type: 'BACHELORS',
    department: 'Computer Science',
    description: 'Undergraduate CS curriculum',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    curriculum_versions: [
      {
        id: 'ver-1',
        version_number: 1,
        academic_year: '2026-2027',
        status: 'DRAFT',
        total_credits_required: 120,
        min_cgpa_required: 2.0,
        is_editable: true,
        created_at: '2026-01-01T00:00:00Z',
      },
    ],
  },
];

vi.mock('../../api/curriculum', () => ({
  curriculumApi: {
    getProgrammes: vi.fn(),
    getCourses: vi.fn(),
    getCurriculumVersion: vi.fn(),
    validateVersion: vi.fn(),
    getPublishPreview: vi.fn(),
    publishVersion: vi.fn(),
    cloneVersion: vi.fn(),
    diffVersions: vi.fn(),
    createRequirementGroup: vi.fn(),
    deleteRequirementGroup: vi.fn(),
    addCourseToGroup: vi.fn(),
    removeCourseFromGroup: vi.fn(),
    createPrerequisiteRule: vi.fn(),
    deletePrerequisiteRule: vi.fn(),
    testRuleHarness: vi.fn(),
  },
}));

describe('CurriculumWorkspacePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (curriculumApi.getProgrammes as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockProgrammes);
    (curriculumApi.getCourses as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockCourses);
    (curriculumApi.getCurriculumVersion as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockVersionDetail);
  });

  it('renders curriculum header and loads programme data', async () => {
    render(
      <BrowserRouter>
        <CurriculumWorkspacePage />
      </BrowserRouter>
    );

    expect(screen.getByText(/curriculum & requirement workspace/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/BSCS - B\.S\. in Computer Science/i)).toBeInTheDocument();
      expect(screen.getByText(/v1 \(2026-2027\) - \[DRAFT\]/i)).toBeInTheDocument();
      expect(screen.getByText('Computer Science Core')).toBeInTheDocument();
      expect(screen.getByText('Intro to Computer Science')).toBeInTheDocument();
      expect(screen.getByText('Data Structures')).toBeInTheDocument();
    });
  });

  it('switches between tabs: courses and prerequisite rules', async () => {
    render(
      <BrowserRouter>
        <CurriculumWorkspacePage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Computer Science Core')).toBeInTheDocument();
    });

    // Switch to Courses tab
    const courseTabBtn = screen.getByRole('button', { name: /course catalogue/i });
    fireEvent.click(courseTabBtn);

    expect(screen.getByText(/institution course catalogue/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/search by code or title/i)).toBeInTheDocument();

    // Switch to Prerequisite Rule Engine tab
    const rulesTabBtn = screen.getByRole('button', { name: /prerequisite rules & test simulator/i });
    fireEvent.click(rulesTabBtn);

    expect(screen.getByText(/prerequisite rules in current version/i)).toBeInTheDocument();
    expect(screen.getByText(/requires cs101 with grade c/i)).toBeInTheDocument();
  });

  it('triggers version validation and displays results', async () => {
    (curriculumApi.validateVersion as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      is_valid: true,
      errors: [],
      warnings: [],
    });

    render(
      <BrowserRouter>
        <CurriculumWorkspacePage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/v1 \(2026-2027\) - \[DRAFT\]/i)).toBeInTheDocument();
    });

    const validateBtn = screen.getByRole('button', { name: /validate rules/i });
    fireEvent.click(validateBtn);

    await waitFor(() => {
      expect(screen.getByText(/validation report: ready for publishing/i)).toBeInTheDocument();
    });
  });

  it('opens and closes Rule Builder Modal', async () => {
    render(
      <BrowserRouter>
        <CurriculumWorkspacePage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/v1 \(2026-2027\) - \[DRAFT\]/i)).toBeInTheDocument();
    });

    // Navigate to rules tab
    fireEvent.click(screen.getByRole('button', { name: /prerequisite rules & test simulator/i }));

    const addRuleBtn = screen.getByRole('button', { name: /\+ author \/ test new rule/i });
    fireEvent.click(addRuleBtn);

    expect(screen.getByRole('heading', { name: /prerequisite rule builder & test harness/i })).toBeInTheDocument();
    expect(screen.getByText(/rule type \(operator\)/i)).toBeInTheDocument();

    // Close modal
    const closeBtn = screen.getByRole('button', { name: /close dialog/i });
    fireEvent.click(closeBtn);

    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: /prerequisite rule builder & test harness/i })).not.toBeInTheDocument();
    });
  });

  it('opens Publish Modal when clicking publish on draft version', async () => {
    (curriculumApi.getPublishPreview as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      curriculum_version_id: 'ver-1',
      programme_code: 'BSCS',
      programme_name: 'B.S. in Computer Science',
      version_number: 1,
      academic_year: '2026-2027',
      total_credits_required: 120,
      min_cgpa_required: 2.0,
      total_requirement_groups: 1,
      total_unique_courses: 2,
      total_prerequisite_rules: 1,
      can_publish: true,
      validation_report: {
        is_valid: true,
        errors: [],
        warnings: [],
      },
    });

    render(
      <BrowserRouter>
        <CurriculumWorkspacePage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/v1 \(2026-2027\) - \[DRAFT\]/i)).toBeInTheDocument();
    });

    const publishBtn = screen.getByRole('button', { name: /publish version/i });
    fireEvent.click(publishBtn);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /curriculum publication preview/i })).toBeInTheDocument();
      expect(screen.getByText(/strict immutability notice/i)).toBeInTheDocument();
    });
  });
});
