export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  timestamp: string;
}

export interface ApiErrorPayload {
  message: string;
  detail?: string;
  code?: string;
  field_errors?: Record<string, string[]>;
}

export type Role =
  | 'STUDENT'
  | 'ADVISOR'
  | 'COORDINATOR'
  | 'HOD'
  | 'ADMIN';

export interface UserProfile {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  institution_id: string;
  institution_name: string;
  role: Role;
}

export interface DemoAcademicSummary {
  programName: string;
  catalogYear: string;
  totalCreditsRequired: number;
  creditsEarned: number;
  creditsInProgress: number;
  cumulativeGpa: string;
  advisorName: string;
  advisorEmail: string;
  auditStatus: 'ON_TRACK' | 'AT_RISK' | 'ACTION_REQUIRED';
}
