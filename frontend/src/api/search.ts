import { apiClient } from './client';

export interface SearchStudentResult {
  id: string;
  registration_number: string;
  username: string;
  name: string;
  email: string;
  programme_code: string;
  programme_name: string;
  cgpa: string;
}

export interface SearchFacultyResult {
  id: string;
  registration_number: string;
  username: string;
  name: string;
  role: string;
  email: string;
}

export interface SearchCourseResult {
  id: string;
  code: string;
  title: string;
  credits: string;
}

export interface SearchProgrammeResult {
  id: string;
  code: string;
  name: string;
  degree_type: string;
}

export interface SearchPlanResult {
  id: string;
  name: string;
  status: string;
  student_id: string;
  student_name: string;
  student_registration_number: string;
  programme_code: string;
}

export interface GlobalSearchResults {
  query: string;
  students: SearchStudentResult[];
  faculty: SearchFacultyResult[];
  courses: SearchCourseResult[];
  programmes: SearchProgrammeResult[];
  plans: SearchPlanResult[];
}

export const searchApi = {
  search: (query: string): Promise<GlobalSearchResults> => {
    return apiClient.get<GlobalSearchResults>('/api/search/', { params: { q: query } });
  },
};
