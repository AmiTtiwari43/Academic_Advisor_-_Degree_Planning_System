import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { authApi, LoginCredentials } from '../api/auth';
import { InstitutionMembershipSummary, Role, UserMe } from '../types';

interface AuthContextType {
  user: UserMe | null;
  activeMembership: InstitutionMembershipSummary | null;
  activeRole: Role | null;
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

  return (
    <AuthContext.Provider
      value={{
        user,
        activeMembership,
        activeRole: activeMembership?.role || null,
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
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
