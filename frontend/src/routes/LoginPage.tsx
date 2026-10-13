import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button, Input } from '../components';
import styles from './LoginPage.module.css';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError('Please provide both username and password.');
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      await login({ username, password });
      navigate('/dashboard');
    } catch (err: unknown) {
      const errorMsg =
        err && typeof err === 'object' && 'payload' in err
          ? (err as { payload: { detail?: string; message?: string } }).payload.detail ||
            (err as { payload: { detail?: string; message?: string } }).payload.message
          : 'Invalid credentials. Please verify your username and password.';
      setError(errorMsg || 'Authentication failed. Please check your credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <div className={styles.header}>
          <h1 className={styles.title}>Academic Sign In</h1>
          <p className={styles.subtitle}>
            Enter your institutional credentials to access your degree plan and advising portal
          </p>
        </div>

        {error && (
          <div className={styles.errorBanner} role="alert">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className={styles.form}>
          <Input
            id="username-input"
            label="Institutional Username or ID"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="e.g. s102938 or jsmith"
            required
            disabled={isSubmitting}
            autoComplete="username"
          />

          <Input
            id="password-input"
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••••••"
            required
            disabled={isSubmitting}
            autoComplete="current-password"
          />

          <div className={styles.actions}>
            <Link to="/forgot-password" className={styles.link}>
              Forgot password?
            </Link>
          </div>

          <Button
            type="submit"
            variant="primary"
            disabled={isSubmitting}
            fullWidth
          >
            {isSubmitting ? 'Authenticating...' : 'Sign In'}
          </Button>
        </form>

        <div className={styles.footer}>
          Protected by institutional session security and multi-tenant isolation.
        </div>
      </div>
    </div>
  );
};
