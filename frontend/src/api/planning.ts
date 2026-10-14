import { apiClient } from './client';

export type PlanStatus =
  | 'DRAFT'
  | 'SUBMITTED'
  | 'UNDER_REVIEW'
  | 'APPROVED'
  | 'RETURNED'
  | 'REJECTED'
  | 'RESUBMITTED'
  | 'SUPERSEDED'
  | 'ARCHIVED';

export type PlanVersionStatus =
  | 'DRAFT'
  | 'SUBMITTED'
  | 'UNDER_REVIEW'
  | 'APPROVED'
  | 'RETURNED'
  | 'REJECTED'
  | 'RESUBMITTED'
  | 'SUPERSEDED'
  | 'ARCHIVED';


export interface PlanItem {
  id: string;
  plan: string;
  course: string;
  course_code: string;
  course_title: string;
  course_credits: string | number;
  planned_term: string;
  planned_term_code: string;
  term_index: number;
  position: number;
  notes?: string;
  created_at?: string;
  updated_at?: string;
}

export interface Plan {
  id: string;
  institution: string;
  student_record: string;
  student_username?: string;
  curriculum_version: string;
  curriculum_version_number?: number;
  programme_name?: string;
  name: string;
  is_primary: boolean;
  status: PlanStatus;
  row_version: number;
  items: PlanItem[];
  created_at: string;
  updated_at: string;
}

export interface PlanSimulationConstraint {
  code: string;
  severity: 'HARD' | 'WARNING';
  message: string;
  course_code?: string;
  term_code?: string;
  term_index?: number;
}

export interface PlanSimulationCourseStatus {
  course_id: string;
  course_code: string;
  course_title: string;
  credits: string | number;
  term_index: number;
  term_code: string;
  is_eligible: boolean;
  prerequisite_satisfied: boolean;
  corequisite_satisfied: boolean;
  offering_available: boolean;
  blocking_reasons: string[];
}

export interface PlanSimulationTermDetail {
  term_id: string;
  term_code: string;
  term_name: string;
  term_index: number;
  total_credits: string | number;
  is_credit_limit_exceeded: boolean;
  is_credit_minimum_met: boolean;
  courses: PlanSimulationCourseStatus[];
}

export interface PlanAuditGroupSummary {
  name: string;
  group_type: string;
  min_credits: number | string;
  earned_credits: number | string;
  is_satisfied: boolean;
}

export interface PlanAuditReportSummary {
  total_credits_required?: number | string;
  total_credits_earned?: number | string;
  remaining_credits_required?: number | string;
  is_degree_satisfied?: boolean;
  groups?: PlanAuditGroupSummary[];
  [key: string]: unknown;
}

export interface PlanSimulationReport {
  plan_id: string;
  plan_name: string;
  student_username: string;
  curriculum_version_number: number;
  total_planned_credits: string;
  total_cumulative_credits: string;
  is_valid_for_submission: boolean;
  hard_constraints: PlanSimulationConstraint[];
  warnings: PlanSimulationConstraint[];
  projected_graduation_term: string | null;
  graduation_projection_reason: string | null;
  audit_report: PlanAuditReportSummary;
  terms: PlanSimulationTermDetail[];
}

export interface PlanVersion {
  id: string;
  institution: string;
  plan: string;
  version_number: number;
  snapshot_data: {
    plan_id: string;
    plan_name: string;
    curriculum_version_id: string;
    curriculum_version_number: number;
    items: Array<{
      course_id: string;
      course_code: string;
      course_title: string;
      credits: string;
      term_id: string;
      term_code: string;
      term_index: number;
      position: number;
      notes?: string;
    }>;
    simulation: PlanSimulationReport;
    submitted_by_username: string;
    submission_note: string;
  };
  status: PlanVersionStatus;
  submitted_by?: number;
  submitted_by_username?: string;
  submission_note?: string;
  submitted_at: string;
}

export interface PlanDiffReport {
  version_a: number;
  version_b: number;
  items_added: Array<{
    course_code: string;
    course_title: string;
    term_code: string;
    term_index: number;
  }>;
  items_removed: Array<{
    course_code: string;
    course_title: string;
    term_code: string;
    term_index: number;
  }>;
  items_moved: Array<{
    course_code: string;
    course_title: string;
    from_term: string;
    from_index: number;
    to_term: string;
    to_index: number;
  }>;
  simulation_a: PlanSimulationReport;
  simulation_b: PlanSimulationReport;
}

export const planningApi = {
  fetchPlans: (studentRecordId?: string): Promise<Plan[]> => {
    const params = studentRecordId ? { student_record: studentRecordId } : undefined;
    return apiClient.get<Plan[]>('/api/v1/plans/', { params });
  },

  fetchPlan: (id: string): Promise<Plan> => {
    return apiClient.get<Plan>(`/api/v1/plans/${id}/`);
  },

  createPlan: (data: {
    student_record: string;
    curriculum_version?: string;
    name: string;
    is_primary?: boolean;
  }): Promise<Plan> => {
    return apiClient.post<Plan>('/api/v1/plans/', data);
  },

  updatePlan: (
    id: string,
    data: { name?: string; is_primary?: boolean; row_version: number }
  ): Promise<Plan> => {
    return apiClient.patch<Plan>(`/api/v1/plans/${id}/`, data);
  },

  deletePlan: (id: string): Promise<void> => {
    return apiClient.delete<void>(`/api/v1/plans/${id}/`);
  },

  addCourseToPlan: (
    planId: string,
    data: {
      course: string;
      planned_term: string;
      term_index: number;
      position?: number;
      notes?: string;
    }
  ): Promise<PlanItem> => {
    return apiClient.post<PlanItem>(`/api/v1/plans/${planId}/add_course/`, data);
  },

  removeCourseFromPlan: (planId: string, itemId: string): Promise<{ status: string }> => {
    return apiClient.post<{ status: string }>(`/api/v1/plans/${planId}/remove_course/`, {
      item_id: itemId,
    });
  },

  moveCourseInPlan: (
    planId: string,
    itemId: string,
    data: {
      target_term: string;
      target_term_index: number;
      target_position?: number;
    }
  ): Promise<PlanItem> => {
    return apiClient.post<PlanItem>(`/api/v1/plans/${planId}/move_course/`, {
      item_id: itemId,
      ...data,
    });
  },

  simulatePlan: (planId: string): Promise<PlanSimulationReport> => {
    return apiClient.post<PlanSimulationReport>(`/api/v1/plans/${planId}/simulate/`);
  },

  submitPlan: (planId: string, submissionNote?: string): Promise<PlanVersion> => {
    return apiClient.post<PlanVersion>(`/api/v1/plans/${planId}/submit/`, {
      submission_note: submissionNote || '',
    });
  },

  fetchPlanVersions: (planId: string): Promise<PlanVersion[]> => {
    return apiClient.get<PlanVersion[]>(`/api/v1/plans/${planId}/versions/`);
  },

  comparePlanVersions: (planId: string, vA: number, vB: number): Promise<PlanDiffReport> => {
    return apiClient.get<PlanDiffReport>(`/api/v1/plans/${planId}/diff/`, {
      params: { version_a: vA, version_b: vB },
    });
  },

  simulateWhatIf: (data: {
    student_record_id: string;
    target_curriculum_version_id: string;
    plan_id?: string;
  }): Promise<PlanSimulationReport> => {
    return apiClient.post<PlanSimulationReport>('/api/v1/planning/what-if/', data);
  },
};
