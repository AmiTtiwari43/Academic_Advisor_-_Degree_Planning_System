import { apiClient } from './client';

export interface Programme {
  id: string;
  code: string;
  name: string;
  degree_type: string;
  department: string;
  description: string;
  is_active: boolean;
  curriculum_versions?: CurriculumVersionSummary[];
  created_at: string;
}

export interface CurriculumVersionSummary {
  id: string;
  version_number: number;
  academic_year: string;
  status: 'DRAFT' | 'PUBLISHED' | 'ARCHIVED';
  total_credits_required: number;
  min_cgpa_required: number;
  published_at?: string | null;
  published_by_username?: string | null;
  change_summary?: string;
  is_editable: boolean;
  created_at: string;
}

export interface Course {
  id: string;
  code: string;
  title: string;
  description: string;
  credits: number;
  default_credit_category_code?: string;
  is_active: boolean;
  created_at: string;
}

export interface RequirementGroupCourse {
  id: string;
  requirement_group: string;
  course: string;
  course_code: string;
  course_title: string;
  course_credits: number;
  is_mandatory: boolean;
  display_order: number;
}

export interface RequirementGroup {
  id: string;
  curriculum_version: string;
  parent?: string | null;
  name: string;
  group_type: 'MANDATORY' | 'ELECTIVE' | 'CREDIT_CATEGORY';
  min_credits: number;
  min_courses: number;
  min_cgpa?: number | null;
  credit_category?: string | null;
  credit_category_code?: string;
  display_order: number;
  group_courses: RequirementGroupCourse[];
  children?: RequirementGroup[];
  created_at: string;
}

export interface PrerequisiteRule {
  id: string;
  curriculum_version: string;
  course: string;
  course_code: string;
  course_title: string;
  rule_json: Record<string, unknown>;
  description: string;
  created_at: string;
}

export interface CurriculumVersionDetail extends CurriculumVersionSummary {
  programme: string;
  programme_code: string;
  programme_name: string;
  requirement_groups: RequirementGroup[];
  prerequisite_rules: PrerequisiteRule[];
}

export interface ValidationIssue {
  code: string;
  message: string;
  entity_type: string;
  entity_id?: string;
  details?: Record<string, unknown>;
}

export interface ValidationReport {
  is_valid: boolean;
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
}

export interface PublishPreview {
  curriculum_version_id: string;
  programme_code: string;
  programme_name: string;
  version_number: number;
  academic_year: string;
  total_credits_required: number;
  min_cgpa_required: number;
  total_requirement_groups: number;
  total_unique_courses: number;
  total_prerequisite_rules: number;
  can_publish: boolean;
  validation_report: ValidationReport;
}

export interface RuleHarnessResult {
  status: 'SATISFIED' | 'UNSATISFIED' | 'INDETERMINATE';
  eligible: boolean;
  is_satisfied: boolean;
  is_indeterminate: boolean;
  blocking_reasons: string[];
  execution_tree: {
    node_path: string;
    type: string;
    status: string;
    explanation: string;
    blocking_reasons: string[];
    children: unknown[];
  };
}

export const curriculumApi = {
  // Programmes
  getProgrammes: () => apiClient.get<Programme[]>('/api/v1/programmes/'),
  getProgramme: (id: string) => apiClient.get<Programme>(`/api/v1/programmes/${id}/`),
  createProgramme: (data: Partial<Programme>) =>
    apiClient.post<Programme>('/api/v1/programmes/', data),

  // Curriculum Versions
  getCurriculumVersion: (id: string) =>
    apiClient.get<CurriculumVersionDetail>(`/api/v1/curricula/${id}/`),
  createProgrammeVersion: (programmeId: string, data: Record<string, unknown>) =>
    apiClient.post<CurriculumVersionDetail>(`/api/v1/programmes/${programmeId}/versions/`, data),
  updateCurriculumVersion: (id: string, data: Record<string, unknown>) =>
    apiClient.patch<CurriculumVersionDetail>(`/api/v1/curricula/${id}/`, data),
  deleteCurriculumVersion: (id: string) => apiClient.delete(`/api/v1/curricula/${id}/`),

  // Publishing & Actions
  validateVersion: (id: string) =>
    apiClient.get<ValidationReport>(`/api/v1/curricula/${id}/validate/`),
  getPublishPreview: (id: string) =>
    apiClient.get<PublishPreview>(`/api/v1/curricula/${id}/preview/`),
  publishVersion: (id: string) =>
    apiClient.post<CurriculumVersionDetail>(`/api/v1/curricula/${id}/publish/`),
  cloneVersion: (id: string, data?: { academic_year?: string }) =>
    apiClient.post<CurriculumVersionDetail>(`/api/v1/curricula/${id}/clone/`, data),
  diffVersions: (id: string, otherId: string) =>
    apiClient.get<Record<string, unknown>>(`/api/v1/curricula/${id}/diff/${otherId}/`),

  // Courses Catalog
  getCourses: () => apiClient.get<Course[]>('/api/v1/courses/'),
  createCourse: (data: Partial<Course>) => apiClient.post<Course>('/api/v1/courses/', data),

  // Requirement Groups
  createRequirementGroup: (data: Record<string, unknown>) =>
    apiClient.post<RequirementGroup>('/api/v1/requirement-groups/', data),
  deleteRequirementGroup: (id: string) =>
    apiClient.delete(`/api/v1/requirement-groups/${id}/`),
  addCourseToGroup: (groupId: string, courseId: string, isMandatory = true) =>
    apiClient.post<RequirementGroupCourse>(`/api/v1/requirement-groups/${groupId}/add_course/`, {
      course_id: courseId,
      is_mandatory: isMandatory,
    }),
  removeCourseFromGroup: (groupId: string, courseId: string) =>
    apiClient.post(`/api/v1/requirement-groups/${groupId}/remove_course/`, {
      course_id: courseId,
    }),

  // Prerequisite Rules
  createPrerequisiteRule: (data: Record<string, unknown>) =>
    apiClient.post<PrerequisiteRule>('/api/v1/prerequisite-rules/', data),
  deletePrerequisiteRule: (id: string) =>
    apiClient.delete(`/api/v1/prerequisite-rules/${id}/`),

  // Rule Test Harness
  testRuleHarness: (ruleJson: Record<string, unknown>, context: Record<string, unknown>) =>
    apiClient.post<RuleHarnessResult>('/api/v1/rules/test-harness/', {
      rule_json: ruleJson,
      context,
    }),
};
