import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ErrorBoundary } from './ErrorBoundary';
import { PublicLayout } from '../layouts/PublicLayout';
import { AppLayout } from '../layouts/AppLayout';
import { LandingPage } from '../routes/LandingPage';
import { DashboardPage } from '../routes/DashboardPage';
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
        <BrowserRouter>
          <Routes>
            {/* Public Entry Routes */}
            <Route element={<PublicLayout />}>
              <Route path="/" element={<LandingPage />} />
            </Route>

            {/* Authenticated Application Shell */}
            <Route element={<AppLayout />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/curriculum" element={<DashboardPage />} />
              <Route path="/plan" element={<DashboardPage />} />
              <Route path="/audit" element={<DashboardPage />} />
              <Route path="/advising" element={<DashboardPage />} />
              <Route path="/careers" element={<DashboardPage />} />
            </Route>

            {/* 404 Route */}
            <Route path="/404" element={<NotFoundPage />} />
            <Route path="*" element={<Navigate to="/404" replace />} />
          </Routes>
        </BrowserRouter>
      </ErrorBoundary>
    </QueryClientProvider>
  );
};
