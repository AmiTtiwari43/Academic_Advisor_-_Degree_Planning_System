import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ErrorBoundary } from './ErrorBoundary';
import { AuthProvider } from '../context/AuthContext';
import { PublicLayout } from '../layouts/PublicLayout';
import { AppLayout } from '../layouts/AppLayout';
import { LandingPage } from '../routes/LandingPage';
import { LoginPage } from '../routes/LoginPage';
import { ForgotPasswordPage } from '../routes/ForgotPasswordPage';
import { ResetPasswordPage } from '../routes/ResetPasswordPage';
import { AccessDeniedPage } from '../routes/AccessDeniedPage';
import { DashboardPage } from '../routes/DashboardPage';
import { CurriculumWorkspacePage } from '../routes/CurriculumWorkspacePage';
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

              {/* Authenticated Application Shell */}
              <Route element={<AppLayout />}>
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/curriculum" element={<CurriculumWorkspacePage />} />
                <Route path="/plan" element={<DashboardPage />} />
                <Route path="/audit" element={<DashboardPage />} />
                <Route path="/advising" element={<DashboardPage />} />
                <Route path="/careers" element={<DashboardPage />} />
                <Route path="/admin" element={<DashboardPage />} />
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
