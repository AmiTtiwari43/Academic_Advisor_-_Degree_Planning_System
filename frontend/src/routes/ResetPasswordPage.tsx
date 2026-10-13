import React, { useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { authApi } from '../api/auth';
import { Button, Input } from '../components';
import styles from './LoginPage.module.css';

export const ResetPasswordPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const uid = searchParams.get('uid') || '';
  const token = searchParams.get('token') || '';

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uid || !token) {
      setError('Invalid or expired password reset link parameters.');
      return;
    }

    if (newPassword.length < 8) {
      setError('New password must contain at least 8 characters.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      await authApi.confirmPasswordReset({
        uid,
        token,
        new_password: newPassword,
      });
      setIsSuccess(true);
    } catch (err: unknown) {
      const errorMsg =
        err && typeof err === 'object' && 'payload' in err
          ? (err as { payload: { detail?: string } }).payload.detail
          : 'Failed to reset password. The token may be expired or invalid.';
      setError(errorMsg || 'Failed to reset password.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <div className={styles.header}>
          <h1 className={styles.title}>Set New Password</h1>
          <p className={styles.subtitle}>
            Choose a strong password to secure your academic account
          </p>
        </div>

        {error && (
          <div className={styles.errorBanner} role="alert">
            {error}
          </div>
        )}

        {isSuccess ? (
          <div>
            <p style={{ marginBottom: 'var(--space-6)', lineHeight: 1.6, color: 'var(--color-text)' }}>
              Your password has been successfully reset. Prior sessions have been terminated.
            </p>
            <Button
              variant="primary"
              fullWidth
              onClick={() => navigate('/login')}
            >
              Sign In with New Password
            </Button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className={styles.form}>
            <Input
              id="new-password"
              label="New Password"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Minimum 8 characters"
              required
              disabled={isSubmitting}
              autoComplete="new-password"
            />

            <Input
              id="confirm-password"
              label="Confirm New Password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Repeat new password"
              required
              disabled={isSubmitting}
              autoComplete="new-password"
            />

            <Button
              type="submit"
              variant="primary"
              disabled={isSubmitting}
              fullWidth
            >
              {isSubmitting ? 'Updating Password...' : 'Update Password'}
            </Button>

            <div className={styles.actions} style={{ justifyContent: 'center' }}>
              <Link to="/login" className={styles.link}>
                Back to Sign In
              </Link>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
