import { apiClient } from './client';

export type RepeatedCoursePolicy = 'BEST_GRADE' | 'LATEST_GRADE' | 'ALL_ATTEMPTS';
export type StudentRecordStatus = 'ACTIVE' | 'ON_LEAVE' | 'PROBATION' | 'GRADUATED' | 'WITHDRAWN';
export type TranscriptEntryStatus = 'ENROLLED' | 'IN_PROGRESS' | 'COMPLETED' | 'DROPPED' | 'FAILED' | 'WITHDRAWN';
export type VerificationStatus = 'UNVERIFIED' | 'PENDING' | 'VERIFIED' | 'REJECTED';

export interface AcademicTerm {
  id: string;
  institution: string;
  code: string;
  name: string;
  season: 'FALL' | 'SPRING' | 'SUMMER' | 'WINTER';
  year: number;
  start_date: string;
  end_date: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TranscriptEntry {
  id: string;
  institution: string;
  student_record: string;
  course: string;
  course_code: string;
  course_title: string;
  term: string;
  term_code: string;
  grade?: string;
  credits_attempted: string | number;
  credits_earned: string | number;
  status: TranscriptEntryStatus;
  verification_status: VerificationStatus;
  attempt_number: number;
  created_at: string;
  updated_at: string;
}

export interface TransferCredit {
  id: string;
  institution: string;
  student_record: string;
  course_code: string;
  course_title: string;
  source_institution: string;
  credits: string | number;
  grade: string;
  is_verified: boolean;
  verified_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Exemption {
  id: string;
  institution: string;
  student_record: string;
  course: string;
  course_code: string;
  course_title: string;
  reason: string;
  approved_by: string;
  approved_by_username: string;
  approved_at: string;
  created_at: string;
  updated_at: string;
}

export interface StudentRecord {
  id: string;
  institution: string;
  student: string;
  student_username: string;
  student_first_name: string;
  student_last_name: string;
  student_email: string;
  programme: string;
  programme_code: string;
  programme_name: string;
  pinned_curriculum: string;
  curriculum_version_number: number;
  enrollment_term: string;
  enrollment_term_code: string;
  expected_graduation_term?: string | null;
  repeated_course_policy: RepeatedCoursePolicy;
  status: StudentRecordStatus;
  cached_cgpa: string | number;
  cached_total_credits: string | number;
  created_at: string;
  updated_at: string;
}

export interface StudentRecordDetail extends StudentRecord {
  transcript_entries: TranscriptEntry[];
  transfer_credits: TransferCredit[];
  exemptions: Exemption[];
}

export interface AllocatedCourse {
  course_id: string;
  course_code: string;
  course_title: string;
  grade: string;
  earned_credits: number;
  source: 'TRANSCRIPT' | 'TRANSFER' | 'EXEMPTION';
  attempt_number?: number;
}

export interface CourseSummary {
  course_id: string;
  course_code: string;
  course_title: string;
  credits: number;
  grade?: string;
}

export interface RequirementGroupAudit {
  group_id: string;
  name: string;
  group_type: 'MANDATORY' | 'ELECTIVE' | 'CREDIT_CATEGORY';
  min_credits: number;
  min_courses: number;
  min_cgpa?: number | null;
  earned_credits: number;
  in_progress_credits: number;
  remaining_credits: number;
  is_satisfied: bool;
  cgpa_satisfied: bool;
  allocated_courses: AllocatedCourse[];
  remaining_mandatory_courses: CourseSummary[];
  in_progress_courses: CourseSummary[];
}

// Ensure boolean compatibility
type bool = boolean;

export interface DegreeAuditReport {
  student_id: string;
  student_username: string;
  programme_code: string;
  programme_name: string;
  version_number: number;
  academic_year: string;
  total_credits_required: number;
  total_credits_earned: number;
  total_credits_in_progress: number;
  remaining_credits_required: number;
  overall_cgpa: number;
  min_cgpa_required: number;
  is_credits_satisfied: boolean;
  is_cgpa_satisfied: boolean;
  is_degree_satisfied: boolean;
  groups: RequirementGroupAudit[];
}

export interface CourseEligibilityResult {
  course_id: string;
  course_code: string;
  course_title: string;
  eligible: boolean;
  status: 'SATISFIED' | 'UNSATISFIED' | 'INDETERMINATE';
  is_satisfied: boolean;
  is_indeterminate: boolean;
  blocking_reasons: string[];
  execution_tree: Record<string, unknown> | null;
}

export const academicRecordsApi = {
  getStudentRecords: (params?: { programme?: string }) =>
    apiClient.get<StudentRecord[]>('/api/v1/student-records/', { params }),

  getStudentRecord: (id: string) =>
    apiClient.get<StudentRecordDetail>(`/api/v1/student-records/${id}/`),

  getStudentRecordAudit: (id: string) =>
    apiClient.get<DegreeAuditReport>(`/api/v1/student-records/${id}/audit/`),

  checkCourseEligibility: (recordId: string, courseId: string, asOfTermId?: string) =>
    apiClient.get<CourseEligibilityResult>(
      `/api/v1/student-records/${recordId}/eligibility/${courseId}/`,
      asOfTermId ? { params: { as_of_term: asOfTermId } } : undefined
    ),

  getStudentRecordTranscript: (id: string) =>
    apiClient.get<TranscriptEntry[]>(`/api/v1/student-records/${id}/transcript/`),

  getTerms: () =>
    apiClient.get<AcademicTerm[]>('/api/v1/terms/'),

  getAcademicTerms: () =>
    apiClient.get<AcademicTerm[]>('/api/v1/terms/'),

  getTransferCredits: (recordId?: string) =>
    apiClient.get<TransferCredit[]>('/api/v1/transfer-credits/', recordId ? { params: { student_record: recordId } } : undefined),

  getExemptions: (recordId?: string) =>
    apiClient.get<Exemption[]>('/api/v1/exemptions/', recordId ? { params: { student_record: recordId } } : undefined),
};
