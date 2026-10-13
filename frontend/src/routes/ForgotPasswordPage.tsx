import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { authApi } from '../api/auth';
import { Button, Input } from '../components';
import styles from './LoginPage.module.css';

export const ForgotPasswordPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) {
      setError('Please provide your institutional email address.');
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      await authApi.requestPasswordReset(email.trim());
      setIsSubmitted(true);
    } catch {
      // Always treat as success to avoid user enumeration
      setIsSubmitted(true);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <div className={styles.header}>
          <h1 className={styles.title}>Reset Password</h1>
          <p className={styles.subtitle}>
            Enter your institutional email address to receive password recovery instructions
          </p>
        </div>

        {error && (
          <div className={styles.errorBanner} role="alert">
            {error}
          </div>
        )}

        {isSubmitted ? (
          <div>
            <p style={{ marginBottom: 'var(--space-6)', lineHeight: 1.6, color: 'var(--color-text)' }}>
              If an account with <strong>{email}</strong> exists in our records, a secure password
              reset link has been dispatched. Please check your inbox.
            </p>
            <Link to="/login">
              <Button variant="secondary" fullWidth>
                Return to Sign In
              </Button>
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className={styles.form}>
            <Input
              id="email-input"
              label="Institutional Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="user@institution.edu"
              required
              disabled={isSubmitting}
              autoComplete="email"
            />

            <Button
              type="submit"
              variant="primary"
              disabled={isSubmitting}
              fullWidth
            >
              {isSubmitting ? 'Sending Instructions...' : 'Send Recovery Link'}
            </Button>

            <div className={styles.actions} style={{ justifyContent: 'center' }}>
              <Link to="/login" className={styles.link}>
                Remember your password? Sign In
              </Link>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
