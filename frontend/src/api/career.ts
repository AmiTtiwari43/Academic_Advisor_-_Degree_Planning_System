import { apiClient } from './client';

export type SkillCategory =
  | 'TECHNICAL'
  | 'SOFT_SKILL'
  | 'DOMAIN_KNOWLEDGE'
  | 'TOOL_OR_PLATFORM';

export type ProficiencyLevel =
  | 'BEGINNER'
  | 'INTERMEDIATE'
  | 'ADVANCED'
  | 'EXPERT';

export interface Skill {
  id: string;
  code: string;
  name: string;
  category: SkillCategory;
  description: string;
  created_at?: string;
  updated_at?: string;
}

export interface CareerSkillRequirement {
  id: string;
  career_objective: string;
  skill: string;
  skill_code: string;
  skill_name: string;
  skill_category: string;
  min_proficiency: ProficiencyLevel;
  is_critical: boolean;
  display_order: number;
}

export interface CareerObjective {
  id: string;
  code: string;
  title: string;
  description: string;
  programme?: string | null;
  programme_code?: string | null;
  is_active: boolean;
  skill_requirements: CareerSkillRequirement[];
  created_at?: string;
  updated_at?: string;
}

export interface CourseSkillMapping {
  id: string;
  course: string;
  course_code: string;
  course_title: string;
  skill: string;
  skill_code: string;
  skill_name: string;
  proficiency_level: ProficiencyLevel;
  coverage_weight: number;
  description: string;
  created_at?: string;
  updated_at?: string;
}

export interface StudentCareerPreference {
  id: string;
  student_record: string;
  career_objective: string;
  career_objective_code: string;
  career_objective_title: string;
  priority: number;
  target_term?: string | null;
  target_term_code?: string | null;
  notes: string;
  created_at?: string;
  updated_at?: string;
}

export interface AcquiredSkillInfo {
  skill_id: string;
  skill_code: string;
  skill_name: string;
  skill_category: string;
  proficiency_level: string;
  proficiency_score: number;
  source_courses: string[];
}

export interface TargetSkillRequirement {
  skill_id: string;
  skill_code: string;
  skill_name: string;
  skill_category: string;
  min_proficiency: string;
  min_proficiency_score: number;
  is_critical: boolean;
  is_met: boolean;
  current_proficiency: string | null;
  current_proficiency_score: number;
  status: string;
}

export interface SkillGapReport {
  student_id: string;
  student_username: string;
  career_objective_id: string;
  career_objective_code: string;
  career_objective_title: string;
  total_target_skills: number;
  total_critical_skills: number;
  critical_skills_met: number;
  recommended_skills_met: number;
  readiness_percentage: number;
  satisfied_skills: TargetSkillRequirement[];
  proficiency_gaps: TargetSkillRequirement[];
  missing_skills: TargetSkillRequirement[];
  acquired_skills: AcquiredSkillInfo[];
}

export interface RecommendedSkillCovered {
  skill_id: string;
  skill_code: string;
  skill_name: string;
  proficiency_level: string;
  is_critical: boolean;
}

export interface CourseRecommendation {
  course_id: string;
  course_code: string;
  course_title: string;
  credits: number;
  relevance_score: number;
  recommendation_type: 'DEGREE_AND_CAREER' | 'CAREER_ELECTIVE' | string;
  satisfies_degree_requirement_group: string | null;
  is_prerequisite_eligible: boolean;
  prerequisite_status_message: string;
  skills_covered: RecommendedSkillCovered[];
  explanation: string;
}

export const careerApi = {
  // Skills CRUD
  getSkills: (params?: { category?: string; search?: string }) =>
    apiClient.get<Skill[]>('/api/career/skills/', { params }),

  createSkill: (data: Partial<Skill>) =>
    apiClient.post<Skill>('/api/career/skills/', data),

  updateSkill: (id: string, data: Partial<Skill>) =>
    apiClient.patch<Skill>(`/api/career/skills/${id}/`, data),

  deleteSkill: (id: string) =>
    apiClient.delete(`/api/career/skills/${id}/`),

  // Career Objectives CRUD
  getObjectives: (params?: { programme?: string; is_active?: boolean }) =>
    apiClient.get<CareerObjective[]>('/api/career/objectives/', { params }),

  createObjective: (data: Partial<CareerObjective>) =>
    apiClient.post<CareerObjective>('/api/career/objectives/', data),

  updateObjective: (id: string, data: Partial<CareerObjective>) =>
    apiClient.patch<CareerObjective>(`/api/career/objectives/${id}/`, data),

  deleteObjective: (id: string) =>
    apiClient.delete(`/api/career/objectives/${id}/`),

  // Course-to-Skill Mappings
  getCourseSkills: (params?: { course?: string; skill?: string }) =>
    apiClient.get<CourseSkillMapping[]>('/api/career/course-skills/', { params }),

  createCourseSkill: (data: Partial<CourseSkillMapping>) =>
    apiClient.post<CourseSkillMapping>('/api/career/course-skills/', data),

  deleteCourseSkill: (id: string) =>
    apiClient.delete(`/api/career/course-skills/${id}/`),

  // Student Preferences
  getPreferences: (params?: { student_record?: string }) =>
    apiClient.get<StudentCareerPreference[]>('/api/career/preferences/', { params }),

  createPreference: (data: {
    career_objective: string;
    priority?: number;
    target_term?: string;
    notes?: string;
    student_record?: string;
  }) => apiClient.post<StudentCareerPreference>('/api/career/preferences/', data),

  deletePreference: (id: string) =>
    apiClient.delete(`/api/career/preferences/${id}/`),

  // Skill-Gap Analysis
  getSkillGap: (params?: { student_id?: string; objective_id?: string }) =>
    apiClient.get<SkillGapReport>('/api/career/skill-gap/', { params }),

  // Explainable Course Recommendations
  getRecommendations: (params?: { student_id?: string; objective_id?: string; limit?: number }) =>
    apiClient.get<CourseRecommendation[]>('/api/career/recommendations/', { params }),
};
