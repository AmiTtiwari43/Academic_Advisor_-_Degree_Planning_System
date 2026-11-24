import React, { createContext, useContext, useEffect, useState, useCallback, useMemo } from 'react';
import { authApi, LoginCredentials } from '../api/auth';
import { InstitutionMembershipSummary, Role, UserMe } from '../types';
import { toUnifiedRole, getRoleDisplayName, UnifiedRole } from '../utils/rbac';

export interface AuthContextType {
  user: UserMe | null;
  activeMembership: InstitutionMembershipSummary | null;
  activeRole: Role | null;
  unifiedRole?: UnifiedRole;
  roleDisplayName?: 'Moderator' | 'Mentor' | 'Student';
  isModerator?: boolean;
  isMentor?: boolean;
  isStudent?: boolean;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  switchMembership: (membershipId: string) => void;
  hasRole: (roles: Role | Role[]) => boolean;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserMe | null>(null);
  const [activeMembership, setActiveMembership] = useState<InstitutionMembershipSummary | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const refreshUser = useCallback(async () => {
    try {
      const userData = await authApi.getMe();
      setUser(userData);
      if (userData.memberships && userData.memberships.length > 0) {
        setActiveMembership((prev) => {
          if (prev && userData.memberships.some((m) => m.id === prev.id)) {
            return userData.memberships.find((m) => m.id === prev.id) || userData.memberships[0];
          }
          return userData.memberships[0];
        });
      } else {
        setActiveMembership(null);
      }
    } catch {
      setUser(null);
      setActiveMembership(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = async (credentials: LoginCredentials) => {
    const userData = await authApi.login(credentials);
    setUser(userData);
    if (userData.memberships && userData.memberships.length > 0) {
      setActiveMembership(userData.memberships[0]);
    } else {
      setActiveMembership(null);
    }
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } finally {
      setUser(null);
      setActiveMembership(null);
    }
  };

  const switchMembership = (membershipId: string) => {
    if (!user) return;
    const found = user.memberships.find((m) => m.id === membershipId);
    if (found) {
      setActiveMembership(found);
    }
  };

  const hasRole = (roles: Role | Role[]): boolean => {
    if (!activeMembership) return false;
    const targetRoles = Array.isArray(roles) ? roles : [roles];
    return targetRoles.includes(activeMembership.role);
  };

  const unifiedRole = useMemo(
    () => toUnifiedRole(activeMembership?.role, user?.is_superuser),
    [activeMembership?.role, user?.is_superuser]
  );

  const roleDisplayName = useMemo(
    () => getRoleDisplayName(activeMembership?.role, user?.is_superuser),
    [activeMembership?.role, user?.is_superuser]
  );

  const isModerator = unifiedRole === 'MODERATOR';
  const isMentor = unifiedRole === 'MENTOR';
  const isStudent = unifiedRole === 'STUDENT';

  return (
    <AuthContext.Provider
      value={{
        user,
        activeMembership,
        activeRole: activeMembership?.role || null,
        unifiedRole,
        roleDisplayName,
        isModerator,
        isMentor,
        isStudent,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        switchMembership,
        hasRole,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    return {
      user: null,
      activeMembership: null,
      activeRole: null,
      unifiedRole: 'STUDENT',
      roleDisplayName: 'Student',
      isModerator: false,
      isMentor: false,
      isStudent: true,
      isAuthenticated: false,
      isLoading: false,
      login: async () => {},
      logout: async () => {},
      switchMembership: () => {},
      hasRole: () => false,
      refreshUser: async () => {},
    };
  }
  return context;
};
