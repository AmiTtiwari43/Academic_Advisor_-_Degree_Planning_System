import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { CareerGuidancePage } from '../CareerGuidancePage';
import {
  careerApi,
  CareerObjective,
  SkillGapReport,
  CourseRecommendation,
  Skill,
  CourseSkillMapping,
} from '../../api/career';
import * as authContext from '../../context/AuthContext';

const mockObjectives: CareerObjective[] = [
  {
    id: 'obj-1',
    code: 'SWE_CLOUD',
    title: 'Cloud Software Engineer',
    description: 'Designs and deploys cloud-native software and distributed systems.',
    is_active: true,
    skill_requirements: [],
  },
  {
    id: 'obj-2',
    code: 'DATA_ENG',
    title: 'Data Engineer',
    description: 'Builds scalable data processing pipelines and warehouse systems.',
    is_active: true,
    skill_requirements: [],
  },
];

const mockSkillGapReport: SkillGapReport = {
  student_id: 'rec-1',
  student_username: 'alex_student',
  career_objective_id: 'obj-1',
  career_objective_code: 'SWE_CLOUD',
  career_objective_title: 'Cloud Software Engineer',
  total_target_skills: 5,
  total_critical_skills: 3,
  critical_skills_met: 2,
  recommended_skills_met: 1,
  readiness_percentage: 72.5,
  satisfied_skills: [
    {
      skill_id: 'sk-1',
      skill_code: 'PYTHON_PROG',
      skill_name: 'Python Programming',
      skill_category: 'TECHNICAL',
      min_proficiency: 'INTERMEDIATE',
      min_proficiency_score: 2,
      is_critical: true,
      is_met: true,
      current_proficiency: 'ADVANCED',
      current_proficiency_score: 3,
      status: 'MET',
    },
  ],
  proficiency_gaps: [
    {
      skill_id: 'sk-2',
      skill_code: 'DISTRIBUTED_SYS',
      skill_name: 'Distributed Systems',
      skill_category: 'TECHNICAL',
      min_proficiency: 'ADVANCED',
      min_proficiency_score: 3,
      is_critical: true,
      is_met: false,
      current_proficiency: 'BEGINNER',
      current_proficiency_score: 1,
      status: 'PARTIAL',
    },
  ],
  missing_skills: [
    {
      skill_id: 'sk-3',
      skill_code: 'KUBERNETES_DEV',
      skill_name: 'Kubernetes & Containers',
      skill_category: 'TOOL_OR_PLATFORM',
      min_proficiency: 'INTERMEDIATE',
      min_proficiency_score: 2,
      is_critical: false,
      is_met: false,
      current_proficiency: null,
      current_proficiency_score: 0,
      status: 'MISSING',
    },
  ],
  acquired_skills: [
    {
      skill_id: 'sk-1',
      skill_code: 'PYTHON_PROG',
      skill_name: 'Python Programming',
      skill_category: 'TECHNICAL',
      proficiency_level: 'ADVANCED',
      proficiency_score: 3,
      source_courses: ['CS101', 'CS201'],
    },
  ],
};

const mockRecommendations: CourseRecommendation[] = [
  {
    course_id: 'c-301',
    course_code: 'CS301',
    course_title: 'Distributed Computing',
    credits: 4.0,
    relevance_score: 0.95,
    recommendation_type: 'DEGREE_AND_CAREER',
    satisfies_degree_requirement_group: 'CS Major Electives',
    is_prerequisite_eligible: true,
    prerequisite_status_message: 'All prerequisites satisfied',
    skills_covered: [
      {
        skill_id: 'sk-2',
        skill_code: 'DISTRIBUTED_SYS',
        skill_name: 'Distributed Systems',
        proficiency_level: 'ADVANCED',
        is_critical: true,
      },
    ],
    explanation: 'Fulfills CS Major Electives requirement while closing critical Distributed Systems skill gap.',
  },
  {
    course_id: 'c-405',
    course_code: 'CS405',
    course_title: 'Cloud DevOps & Containerization',
    credits: 3.0,
    relevance_score: 0.82,
    recommendation_type: 'CAREER_ELECTIVE',
    satisfies_degree_requirement_group: null,
    is_prerequisite_eligible: false,
    prerequisite_status_message: 'Requires prerequisite CS201',
    skills_covered: [
      {
        skill_id: 'sk-3',
        skill_code: 'KUBERNETES_DEV',
        skill_name: 'Kubernetes & Containers',
        proficiency_level: 'INTERMEDIATE',
        is_critical: false,
      },
    ],
    explanation: 'Career elective addressing missing Kubernetes & Containers competency.',
  },
];

const mockSkills: Skill[] = [
  {
    id: 'sk-1',
    code: 'PYTHON_PROG',
    name: 'Python Programming',
    category: 'TECHNICAL',
    description: 'Object-oriented programming and scripting with Python.',
  },
  {
    id: 'sk-2',
    code: 'DISTRIBUTED_SYS',
    name: 'Distributed Systems',
    category: 'TECHNICAL',
    description: 'Consensus algorithms, replication, and distributed consensus.',
  },
];

const mockMappings: CourseSkillMapping[] = [
  {
    id: 'm-1',
    course: 'c-101',
    course_code: 'CS101',
    course_title: 'Intro to Computer Science',
    skill: 'sk-1',
    skill_code: 'PYTHON_PROG',
    skill_name: 'Python Programming',
    proficiency_level: 'INTERMEDIATE',
    coverage_weight: 0.8,
    description: 'Core programming lab curriculum.',
  },
];

describe('CareerGuidancePage', () => {
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
      hasRole: (roles) => {
        const arr = Array.isArray(roles) ? roles : [roles];
        return arr.includes('COORDINATOR');
      },
      refreshUser: vi.fn(),
    });

    vi.spyOn(careerApi, 'getObjectives').mockResolvedValue(mockObjectives);
    vi.spyOn(careerApi, 'getSkillGap').mockResolvedValue(mockSkillGapReport);
    vi.spyOn(careerApi, 'getRecommendations').mockResolvedValue(mockRecommendations);
    vi.spyOn(careerApi, 'getSkills').mockResolvedValue(mockSkills);
    vi.spyOn(careerApi, 'getCourseSkills').mockResolvedValue(mockMappings);
    vi.spyOn(careerApi, 'createPreference').mockResolvedValue({} as any);
    vi.spyOn(careerApi, 'createSkill').mockResolvedValue({
      id: 'sk-new',
      code: 'RUST_DEV',
      name: 'Rust Development',
      category: 'TECHNICAL',
      description: 'Systems programming in Rust',
    });
  });

  it('renders advisory notice banner prominently', async () => {
    render(<CareerGuidancePage />);

    expect(await screen.findByText(/Advisory Notice:/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Career skill recommendations and readiness scores are designed for academic planning guidance only/i),
    ).toBeInTheDocument();
  });

  it('loads objectives and renders the skill-gap analysis view', async () => {
    render(<CareerGuidancePage />);

    expect(await screen.findByText('73%')).toBeInTheDocument(); // 72.5% rounded
    expect(screen.getByText('2 / 3')).toBeInTheDocument(); // Critical skills met
    expect(screen.getByText('Satisfied Skills (1)')).toBeInTheDocument();
    expect(screen.getByText('Python Programming')).toBeInTheDocument();
    expect(screen.getByText(/Acquired in: CS101, CS201/i)).toBeInTheDocument();
    expect(screen.getByText('Proficiency Gaps (1)')).toBeInTheDocument();
    expect(screen.getByText('Distributed Systems')).toBeInTheDocument();
    expect(screen.getByText('Missing Skills (1)')).toBeInTheDocument();
    expect(screen.getByText('Kubernetes & Containers')).toBeInTheDocument();
  });

  it('switches to Course Recommendations tab and displays degree-respecting recommendations', async () => {
    render(<CareerGuidancePage />);

    const recsTab = await screen.findByRole('tab', { name: /Course Recommendations/i });
    fireEvent.click(recsTab);

    expect(await screen.findByText('CS301: Distributed Computing')).toBeInTheDocument();
    expect(screen.getByText('Degree Requirement & Career')).toBeInTheDocument();
    expect(screen.getByText('Prerequisites Met')).toBeInTheDocument();
    expect(screen.getByText(/Fulfills CS Major Electives requirement/i)).toBeInTheDocument();

    expect(screen.getByText('CS405: Cloud DevOps & Containerization')).toBeInTheDocument();
    expect(screen.getByText('Career Elective')).toBeInTheDocument();
    expect(screen.getByText(/Prerequisites Pending \(Requires prerequisite CS201\)/i)).toBeInTheDocument();
  });

  it('switches to Skills & Course Mappings tab and displays taxonomy table', async () => {
    render(<CareerGuidancePage />);

    const taxonomyTab = await screen.findByRole('tab', { name: /Skills & Course Mappings/i });
    fireEvent.click(taxonomyTab);

    expect(await screen.findByText('Master Skill Taxonomy')).toBeInTheDocument();
    expect(screen.getByText('DISTRIBUTED_SYS')).toBeInTheDocument();
    expect(screen.getByText('Course-to-Skill Mappings')).toBeInTheDocument();
    expect(screen.getByText('CS101')).toBeInTheDocument();
  });

  it('allows coordinator to open Add Skill dialog and save new competency', async () => {
    render(<CareerGuidancePage />);

    const taxonomyTab = await screen.findByRole('tab', { name: /Skills & Course Mappings/i });
    fireEvent.click(taxonomyTab);

    const addBtn = await screen.findByRole('button', { name: /Add Skill/i });
    fireEvent.click(addBtn);

    expect(screen.getByText('Add New Competency / Skill')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/Skill Code/i), { target: { value: 'RUST_DEV' } });
    fireEvent.change(screen.getByLabelText(/Skill Name/i), { target: { value: 'Rust Development' } });
    fireEvent.change(screen.getByLabelText(/Description/i), { target: { value: 'Systems programming' } });

    const submitBtn = screen.getByRole('button', { name: /Save Skill/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(careerApi.createSkill).toHaveBeenCalledWith({
        code: 'RUST_DEV',
        name: 'Rust Development',
        category: 'TECHNICAL',
        description: 'Systems programming',
      });
    });
  });

  it('handles skill gap loading error with retry button', async () => {
    vi.spyOn(careerApi, 'getSkillGap').mockRejectedValue(new Error('Network error'));

    render(<CareerGuidancePage />);

    expect(
      await screen.findByText(/Failed to load skill-gap analysis for selected career objective/i),
    ).toBeInTheDocument();

    vi.spyOn(careerApi, 'getSkillGap').mockResolvedValue(mockSkillGapReport);
    const retryBtn = screen.getByRole('button', { name: /Retry Request/i });
    fireEvent.click(retryBtn);

    expect(await screen.findByText('73%')).toBeInTheDocument();
  });
});
