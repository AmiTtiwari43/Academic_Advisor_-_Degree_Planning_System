import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ErrorBoundary } from './ErrorBoundary';
import { AuthProvider } from '../context/AuthContext';
import { RoleRoute } from '../components/Auth/RoleRoute';
import { PublicLayout } from '../layouts/PublicLayout';
import { AppLayout } from '../layouts/AppLayout';
import { LandingPage } from '../routes/LandingPage';
import { LoginPage } from '../routes/LoginPage';
import { ForgotPasswordPage } from '../routes/ForgotPasswordPage';
import { ResetPasswordPage } from '../routes/ResetPasswordPage';
import { AccessDeniedPage } from '../routes/AccessDeniedPage';
import { DashboardPage } from '../routes/DashboardPage';
import { CurriculumWorkspacePage } from '../routes/CurriculumWorkspacePage';
import { DegreePlannerPage } from '../routes/DegreePlannerPage';
import { DegreeAuditPage } from '../routes/DegreeAuditPage';
import { AdvisorWorkspacePage } from '../routes/AdvisorWorkspacePage';
import { AnalyticsDashboardPage } from '../routes/AnalyticsDashboardPage';
import { CareerGuidancePage } from '../routes/CareerGuidancePage';
import { ProfilePage } from '../routes/ProfilePage';
import { NotFoundPage } from '../routes/NotFoundPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              {/* Public Entry Routes */}
              <Route element={<PublicLayout />}>
                <Route path="/" element={<LandingPage />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/forgot-password" element={<ForgotPasswordPage />} />
                <Route path="/reset-password" element={<ResetPasswordPage />} />
              </Route>

              {/* Authenticated Application Shell with Strict RBAC Panels */}
              <Route element={<AppLayout />}>
                <Route
                  path="/dashboard"
                  element={
                    <RoleRoute allowedRoles={['STUDENT', 'MENTOR', 'MODERATOR']}>
                      <DashboardPage />
                    </RoleRoute>
                  }
                />
                <Route
                  path="/curriculum"
                  element={
                    <RoleRoute allowedRoles={['MODERATOR']}>
                      <CurriculumWorkspacePage />
                    </RoleRoute>
                  }
                />
                <Route
                  path="/plan"
                  element={
                    <RoleRoute allowedRoles={['STUDENT', 'MENTOR', 'MODERATOR']}>
                      <DegreePlannerPage />
                    </RoleRoute>
                  }
                />
                <Route
                  path="/audit"
                  element={
                    <RoleRoute allowedRoles={['STUDENT', 'MENTOR', 'MODERATOR']}>
                      <DegreeAuditPage />
                    </RoleRoute>
                  }
                />
                <Route
                  path="/advising"
                  element={
                    <RoleRoute allowedRoles={['MENTOR', 'MODERATOR']}>
                      <AdvisorWorkspacePage />
                    </RoleRoute>
                  }
                />
                <Route
                  path="/analytics"
                  element={
                    <RoleRoute allowedRoles={['MODERATOR']}>
                      <AnalyticsDashboardPage />
                    </RoleRoute>
                  }
                />
                <Route
                  path="/careers"
                  element={
                    <RoleRoute allowedRoles={['STUDENT', 'MENTOR', 'MODERATOR']}>
                      <CareerGuidancePage />
                    </RoleRoute>
                  }
                />
                <Route
                  path="/admin"
                  element={
                    <RoleRoute allowedRoles={['MODERATOR']}>
                      <DashboardPage />
                    </RoleRoute>
                  }
                />
                <Route
                  path="/profile"
                  element={
                    <RoleRoute allowedRoles={['STUDENT', 'MENTOR', 'MODERATOR']}>
                      <ProfilePage />
                    </RoleRoute>
                  }
                />
              </Route>

              {/* Status & Error Routes */}
              <Route path="/403" element={<AccessDeniedPage />} />
              <Route path="/404" element={<NotFoundPage />} />
              <Route path="*" element={<Navigate to="/404" replace />} />
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </ErrorBoundary>
    </QueryClientProvider>
  );
};
