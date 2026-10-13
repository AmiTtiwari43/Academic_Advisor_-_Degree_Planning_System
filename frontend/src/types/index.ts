export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  timestamp: string;
}

export interface ApiErrorPayload {
  message?: string;
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

export interface InstitutionSummary {
  id: string;
  name: string;
  code: string;
  domain?: string;
}

export interface InstitutionMembershipSummary {
  id: string;
  institution_id: string;
  institution_name: string;
  institution_code: string;
  role: Role;
  is_active: boolean;
}

export interface UserMe {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  preferred_name: string;
  phone_number: string;
  memberships: InstitutionMembershipSummary[];
  is_staff: boolean;
  is_superuser: boolean;
}

export interface UserProfileData {
  phone_number: string;
  preferred_name: string;
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
