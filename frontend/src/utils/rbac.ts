import { Role } from '../types';

export type UnifiedRole = 'MODERATOR' | 'MENTOR' | 'STUDENT';

/**
 * Normalizes institutional database roles into the 3 standardized personas:
 * 1. Moderator (Super Admin, Coordinators, HODs, System Administrators)
 * 2. Mentor (Faculty Advisors, Mentors)
 * 3. Student (Students)
 */
export const toUnifiedRole = (
  role?: Role | string | null,
  isSuperuser?: boolean
): UnifiedRole => {
  if (isSuperuser) return 'MODERATOR';
  if (!role) return 'STUDENT';

  const normalized = role.toUpperCase();
  if (['ADMIN', 'COORDINATOR', 'HOD', 'MODERATOR'].includes(normalized)) {
    return 'MODERATOR';
  }
  if (['ADVISOR', 'FACULTY', 'MENTOR'].includes(normalized)) {
    return 'MENTOR';
  }
  return 'STUDENT';
};

/**
 * Returns human-readable display label for the role.
 */
export const getRoleDisplayName = (
  role?: Role | string | null,
  isSuperuser?: boolean
): 'Moderator' | 'Mentor' | 'Student' => {
  const unified = toUnifiedRole(role, isSuperuser);
  switch (unified) {
    case 'MODERATOR':
      return 'Moderator';
    case 'MENTOR':
      return 'Mentor';
    case 'STUDENT':
      return 'Student';
  }
};

/**
 * Strict RBAC panel authorization matrix:
 * Defines exactly which panels and tasks each of the 3 roles is permitted to access.
 * No extra, no less.
 */
export const ROLE_PANELS: Record<UnifiedRole, string[]> = {
  STUDENT: ['/dashboard', '/plan', '/audit', '/careers', '/profile'],
  MENTOR: ['/dashboard', '/advising', '/plan', '/audit', '/careers', '/profile'],
  MODERATOR: [
    '/dashboard',
    '/advising',
    '/curriculum',
    '/analytics',
    '/plan',
    '/audit',
    '/careers',
    '/admin',
    '/profile',
  ],
};

/**
 * Checks whether the given unified role has permission to access a specific route/panel.
 */
export const canAccessPanel = (role: UnifiedRole, path: string): boolean => {
  const allowed = ROLE_PANELS[role] || [];
  // Match prefix or exact
  return allowed.some((allowedPath) => path === allowedPath || path.startsWith(`${allowedPath}/`));
};
