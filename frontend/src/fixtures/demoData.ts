import { DemoAcademicSummary } from '../types';

/**
 * Fixture: Demo Data for Initial Platform Prototype Shell
 * Notice: This data is explicitly labelled as demo data across UI views.
 * It contains no invented business rules or authoritative calculations.
 */
export const DEMO_STUDENT_SUMMARY: DemoAcademicSummary = {
  programName: 'B.Sc. in Computer Science',
  catalogYear: '2024–2025',
  totalCreditsRequired: 120,
  creditsEarned: 64,
  creditsInProgress: 16,
  cumulativeGpa: '3.78',
  advisorName: 'Dr. Eleanor Vance',
  advisorEmail: 'e.vance@institution.edu',
  auditStatus: 'ON_TRACK',
};

export interface DemoCourseItem {
  id: string;
  code: string;
  title: string;
  credits: number;
  grade: string;
  term: string;
  status: 'COMPLETED' | 'IN_PROGRESS' | 'PLANNED';
}

export const DEMO_COURSES: DemoCourseItem[] = [
  { id: '1', code: 'CS 101', title: 'Introduction to Computer Science', credits: 4, grade: 'A', term: 'Fall 2024', status: 'COMPLETED' },
  { id: '2', code: 'MATH 151', title: 'Calculus I', credits: 4, grade: 'A-', term: 'Fall 2024', status: 'COMPLETED' },
  { id: '3', code: 'ENG 101', title: 'Academic Writing & Rhetoric', credits: 3, grade: 'B+', term: 'Fall 2024', status: 'COMPLETED' },
  { id: '4', code: 'CS 102', title: 'Data Structures & Algorithms', credits: 4, grade: 'A', term: 'Spring 2025', status: 'COMPLETED' },
  { id: '5', code: 'MATH 152', title: 'Calculus II', credits: 4, grade: 'B+', term: 'Spring 2025', status: 'COMPLETED' },
  { id: '6', code: 'CS 201', title: 'Computer Architecture & Systems', credits: 4, grade: '—', term: 'Fall 2025', status: 'IN_PROGRESS' },
  { id: '7', code: 'STAT 200', title: 'Applied Probability & Statistics', credits: 3, grade: '—', term: 'Fall 2025', status: 'IN_PROGRESS' },
  { id: '8', code: 'CS 310', title: 'Database Systems & Relational Theory', credits: 4, grade: '—', term: 'Spring 2026', status: 'PLANNED' },
  { id: '9', code: 'CS 320', title: 'Operating Systems & Concurrency', credits: 4, grade: '—', term: 'Spring 2026', status: 'PLANNED' },
];

export const DEMO_PROGRAM_GROUPS = [
  { id: 'g1', name: 'General Education Foundation', requiredCredits: 24, completedCredits: 21, satisfied: false },
  { id: 'g2', name: 'Core Computer Science', requiredCredits: 48, completedCredits: 28, satisfied: false },
  { id: 'g3', name: 'Mathematics & Quantitative Analysis', requiredCredits: 18, completedCredits: 11, satisfied: false },
  { id: 'g4', name: 'Upper-Division CS Electives', requiredCredits: 18, completedCredits: 0, satisfied: false },
  { id: 'g5', name: 'Open Free Electives', requiredCredits: 12, completedCredits: 4, satisfied: false },
];
