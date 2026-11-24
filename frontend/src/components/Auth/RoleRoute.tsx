import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { UnifiedRole } from '../../utils/rbac';

export interface RoleRouteProps {
  allowedRoles: UnifiedRole[];
  children: React.ReactElement;
}

/**
 * Strict RBAC Route Guard.
 * Restricts access to specific panels and tasks based on the 3 standardized roles:
 * - Moderator
 * - Mentor
 * - Student
 *
 * Unauthenticated users are sent to /login.
 * Unauthorized users are redirected to /403 (Access Denied).
 */
export const RoleRoute: React.FC<RoleRouteProps> = ({ allowedRoles, children }) => {
  const { isAuthenticated, isLoading, unifiedRole } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return null;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  const currentUnifiedRole: UnifiedRole = unifiedRole || 'STUDENT';

  if (!allowedRoles.includes(currentUnifiedRole)) {
    return (
      <Navigate
        to="/403"
        state={{
          deniedPath: location.pathname,
          requiredRoles: allowedRoles,
          currentRole: currentUnifiedRole,
        }}
        replace
      />
    );
  }

  return children;
};
