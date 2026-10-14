import { apiClient } from './client';
import { PlanStatus, PlanVersionStatus } from './planning';

export interface ReviewQueueItem {
  plan_id: string;
  plan_name: string;
  status: PlanStatus;
  row_version: number;
  student_id: string;
  student_username: string;
  student_email: string;
  programme_code: string;
  programme_name: string;
  latest_version_id: string | null;
  latest_version_number: number;
  latest_version_status: PlanVersionStatus;
  submitted_at: string;
  waiting_days: number;
  override_count: number;
  hard_constraints_count: number;
  warnings_count: number;
  is_valid_for_submission: boolean;
  projected_graduation_term: string | null;
}

export type ReviewActionType = 'START_REVIEW' | 'APPROVE' | 'RETURN' | 'REJECT';

export interface PlanReviewDecision {
  id: string;
  institution: string;
  plan: string;
  plan_version: string;
  version_number: number;
  reviewer: number;
  reviewer_username: string;
  reviewer_first_name?: string;
  reviewer_last_name?: string;
  action: ReviewActionType;
  from_status: string;
  to_status: string;
  comments: string;
  idempotency_key?: string | null;
  created_at: string;
}

export type OverrideType =
  | 'PREREQUISITE_OVERRIDE'
  | 'CREDIT_CEILING_OVERRIDE'
  | 'OFFERING_OVERRIDE'
  | 'GENERAL_OVERRIDE';

export interface OverrideEvent {
  id: string;
  institution: string;
  plan: string;
  plan_version: string;
  version_number: number;
  actor: number;
  actor_username: string;
  actor_first_name?: string;
  actor_last_name?: string;
  override_type: OverrideType;
  justification: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface PlanAuditLog {
  id: string;
  institution: string;
  plan: string;
  plan_version?: string | null;
  version_number?: number | null;
  actor?: number | null;
  actor_username?: string;
  action: string;
  from_status: string;
  to_status: string;
  comment: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export const advisingApi = {
  fetchQueue: (params?: { status?: string; programme?: string }): Promise<ReviewQueueItem[]> => {
    return apiClient.get<ReviewQueueItem[]>('/api/v1/advising/queue/', { params });
  },

  startReview: (
    planId: string,
    payload?: { expected_row_version?: number; idempotency_key?: string; version_number?: number }
  ): Promise<PlanReviewDecision> => {
    return apiClient.post<PlanReviewDecision>(`/api/v1/plans/${planId}/start-review/`, payload || {});
  },

  approvePlan: (
    planId: string,
    payload?: {
      comments?: string;
      expected_row_version?: number;
      idempotency_key?: string;
      version_number?: number;
    }
  ): Promise<PlanReviewDecision> => {
    return apiClient.post<PlanReviewDecision>(`/api/v1/plans/${planId}/approve/`, payload || {});
  },

  returnPlan: (
    planId: string,
    payload: {
      comments: string;
      expected_row_version?: number;
      idempotency_key?: string;
      version_number?: number;
    }
  ): Promise<PlanReviewDecision> => {
    return apiClient.post<PlanReviewDecision>(`/api/v1/plans/${planId}/return/`, payload);
  },

  rejectPlan: (
    planId: string,
    payload: {
      comments: string;
      expected_row_version?: number;
      idempotency_key?: string;
      version_number?: number;
    }
  ): Promise<PlanReviewDecision> => {
    return apiClient.post<PlanReviewDecision>(`/api/v1/plans/${planId}/reject/`, payload);
  },

  recordOverride: (
    planId: string,
    payload: {
      override_type: OverrideType;
      justification: string;
      version_number?: number;
      metadata?: Record<string, unknown>;
    }
  ): Promise<OverrideEvent> => {
    return apiClient.post<OverrideEvent>(`/api/v1/plans/${planId}/override/`, payload);
  },

  fetchAuditHistory: (planId: string): Promise<PlanAuditLog[]> => {
    return apiClient.get<PlanAuditLog[]>(`/api/v1/plans/${planId}/audit-history/`);
  },

  fetchReviews: (planId: string): Promise<PlanReviewDecision[]> => {
    return apiClient.get<PlanReviewDecision[]>(`/api/v1/plans/${planId}/reviews/`);
  },

  fetchOverrides: (planId: string): Promise<OverrideEvent[]> => {
    return apiClient.get<OverrideEvent[]>(`/api/v1/plans/${planId}/overrides/`);
  },
};
