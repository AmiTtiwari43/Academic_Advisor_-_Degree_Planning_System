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
  | 'ADMIN'
  | 'MENTOR'
  | 'MODERATOR';

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
  registration_number?: string;
  memberships: InstitutionMembershipSummary[];
  is_staff: boolean;
  is_superuser: boolean;
}

export interface UserProfileData {
  username?: string;
  registration_number?: string;
  first_name?: string;
  last_name?: string;
  preferred_name: string;
  email?: string;
  phone_number: string;
  role?: string;
  institution_name?: string;
  academic_summary?: {
    programme?: string;
    programme_code?: string;
    cgpa?: string;
    credits_earned?: number;
    status?: string;
    enrollment_term?: string;
    advisor?: string;
  };
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
