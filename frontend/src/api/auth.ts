import { apiClient } from './client';
import {
  InstitutionSummary,
  UserMe,
  UserProfileData,
} from '../types';

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface PasswordResetConfirmData {
  uid: string;
  token: string;
  new_password: string;
}

export const authApi = {
  login: (credentials: LoginCredentials) =>
    apiClient.post<UserMe>('/api/auth/login/', credentials),

  logout: () =>
    apiClient.post<{ detail: string }>('/api/auth/logout/'),

  getMe: () =>
    apiClient.get<UserMe>('/api/auth/me/'),

  getProfile: () =>
    apiClient.get<UserProfileData>('/api/auth/profile/'),

  updateProfile: (data: Partial<UserProfileData>) =>
    apiClient.patch<UserProfileData>('/api/auth/profile/', data),

  requestPasswordReset: (email: string) =>
    apiClient.post<{ detail: string }>('/api/auth/password-reset/', { email }),

  confirmPasswordReset: (data: PasswordResetConfirmData) =>
    apiClient.post<{ detail: string }>('/api/auth/password-reset/confirm/', data),

  getInstitutions: () =>
    apiClient.get<InstitutionSummary[]>('/api/institutions/'),
};
