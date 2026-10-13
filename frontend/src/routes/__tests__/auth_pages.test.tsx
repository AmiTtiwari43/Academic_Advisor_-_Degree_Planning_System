import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { LoginPage } from '../LoginPage';
import { ForgotPasswordPage } from '../ForgotPasswordPage';
import { ResetPasswordPage } from '../ResetPasswordPage';
import { AccessDeniedPage } from '../AccessDeniedPage';
import { AuthProvider } from '../../context/AuthContext';
import { authApi } from '../../api/auth';

vi.mock('../../api/auth', () => ({
  authApi: {
    login: vi.fn(),
    logout: vi.fn(),
    getMe: vi.fn().mockRejectedValue(new Error('Not logged in')),
    requestPasswordReset: vi.fn().mockResolvedValue({ detail: 'Sent' }),
    confirmPasswordReset: vi.fn().mockResolvedValue({ detail: 'Success' }),
  },
}));

describe('Authentication Pages', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders LoginPage with accessible inputs and forgot password link', () => {
    render(
      <BrowserRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </BrowserRouter>
    );

    expect(screen.getByRole('heading', { name: /academic sign in/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/institutional username or id/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /forgot password\?/i })).toBeInTheDocument();
  });

  it('handles LoginPage form submission and error state', async () => {
    (authApi.login as unknown as ReturnType<typeof vi.fn>).mockRejectedValueOnce({
      payload: { detail: 'Invalid credentials.' },
    });

    render(
      <BrowserRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </BrowserRouter>
    );

    fireEvent.change(screen.getByLabelText(/institutional username or id/i), {
      target: { value: 'baduser' },
    });
    fireEvent.change(screen.getByLabelText(/^password/i), {
      target: { value: 'wrongpass' },
    });

    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Invalid credentials.');
    });
  });

  it('renders ForgotPasswordPage and displays anti-enumeration success message', async () => {
    render(
      <BrowserRouter>
        <ForgotPasswordPage />
      </BrowserRouter>
    );

    expect(screen.getByRole('heading', { name: /reset password/i })).toBeInTheDocument();
    const emailInput = screen.getByLabelText(/institutional email/i);
    expect(emailInput).toBeInTheDocument();

    fireEvent.change(emailInput, { target: { value: 'student@alpha.edu' } });
    fireEvent.click(screen.getByRole('button', { name: /send recovery link/i }));

    await waitFor(() => {
      expect(screen.getByText(/If an account with/i)).toBeInTheDocument();
      expect(screen.getByText('student@alpha.edu')).toBeInTheDocument();
    });
  });

  it('renders ResetPasswordPage and enforces password match validation', async () => {
    render(
      <MemoryRouter initialEntries={['/reset-password?uid=MQ&token=test-token-123']}>
        <ResetPasswordPage />
      </MemoryRouter>
    );

    expect(screen.getByRole('heading', { name: /set new password/i })).toBeInTheDocument();

    const newPassInput = screen.getByLabelText(/^new password/i);
    const confirmPassInput = screen.getByLabelText(/confirm new password/i);

    fireEvent.change(newPassInput, { target: { value: 'Password123!' } });
    fireEvent.change(confirmPassInput, { target: { value: 'MismatchPassword!' } });

    fireEvent.click(screen.getByRole('button', { name: /update password/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Passwords do not match.');
    });
  });

  it('renders AccessDeniedPage with 403 message and dashboard action', () => {
    render(
      <BrowserRouter>
        <AccessDeniedPage />
      </BrowserRouter>
    );

    expect(screen.getByText(/403 — Access Denied/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /return to dashboard/i })).toBeInTheDocument();
  });
});
