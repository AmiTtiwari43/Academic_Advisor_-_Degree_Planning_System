import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, Calendar, CheckCircle2, Shield, Users, AlertCircle } from 'lucide-react';
import styles from './LandingPage.module.css';
import { Button } from '../components/Button/Button';
import { Input } from '../components/Input/Input';
import { Badge } from '../components/Badge/Badge';
import { useAuth } from '../context/AuthContext';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const { login, isAuthenticated } = useAuth();
  const [identifier, setIdentifier] = useState('student_alex');
  const [password, setPassword] = useState('Password123!');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!identifier.trim() || !password) {
      setError('Please provide username/email and password.');
      return;
    }

    setError(null);
    setIsSubmitting(true);
    try {
      await login({ username: identifier.trim(), password });
      navigate('/dashboard');
    } catch {
      setError('Invalid credentials. Please verify your username and password.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQuickLogin = async (username: string) => {
    setError(null);
    setIsSubmitting(true);
    try {
      await login({ username, password: 'Password123!' });
      navigate('/dashboard');
    } catch {
      setError(`Failed to sign in as ${username}. Ensure demo dataset is seeded.`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={styles.landingContainer}>
      <section className={styles.heroSection}>
        <div className={styles.heroContent}>
          <div className={styles.identityBadge}>
            <Badge variant="teal" size="md" icon={<Shield size={12} />}>
              P02 Institutional Architecture
            </Badge>
          </div>
          <h1 className={styles.heroTitle}>
            Authoritative Curriculum Rules & Degree Planning Platform
          </h1>
          <p className={styles.heroDescription}>
            A rigorous multi-tenant system for higher education institutions. Define versioned
            academic curricula, evaluate prerequisite rules via a sandboxed deterministic engine, audit
            graduation progress, and orchestrate advisor approval workflows.
          </p>

          <div className={styles.pillarsGrid}>
            <div className={styles.pillarCard}>
              <div className={styles.pillarIcon}>
                <BookOpen size={20} />
              </div>
              <h3 className={styles.pillarTitle}>Immutable Curricula</h3>
              <p className={styles.pillarText}>
                Curriculum versions are strictly pinned to students upon matriculation. Published rules
                cannot be modified, preserving institutional academic integrity.
              </p>
            </div>

            <div className={styles.pillarCard}>
              <div className={styles.pillarIcon}>
                <Calendar size={20} />
              </div>
              <h3 className={styles.pillarTitle}>Non-Destructive Simulation</h3>
              <p className={styles.pillarText}>
                Students simulate future semester pathways and what-if scenarios without ever mutating
                official transcripts or institutional degree audits.
              </p>
            </div>

            <div className={styles.pillarCard}>
              <div className={styles.pillarIcon}>
                <Users size={20} />
              </div>
              <h3 className={styles.pillarTitle}>Advisor Governance</h3>
              <p className={styles.pillarText}>
                Every requirement override demands verified advisor authorization, mandatory justification,
                and creates an immutable event audit trail.
              </p>
            </div>
          </div>
        </div>

        {/* Sign In Card */}
        <div className={styles.authContainer}>
          <div className={styles.authCard}>
            <div className={styles.authHeader}>
              <h2 className={styles.authTitle}>Institutional Sign-In</h2>
              <p className={styles.authSub}>Access your institution's academic workspace</p>
            </div>

            {error && (
              <div className={styles.errorBanner} role="alert">
                <AlertCircle size={14} />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSignIn} className={styles.authForm}>
              <Input
                label="Institutional Username or Email"
                type="text"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                placeholder="e.g. student_alex or alex@agu.edu"
                required
                disabled={isSubmitting}
              />
              <Input
                label="Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={isSubmitting}
              />

              <div className={styles.authNote}>
                <CheckCircle2 size={14} className={styles.noteIcon} />
                <span>Default Password for all seeded accounts: <strong>Password123!</strong></span>
              </div>

              <Button
                type="submit"
                variant="primary"
                size="md"
                className={styles.submitButton}
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Authenticating...' : 'Sign In to Workspace'}
              </Button>
            </form>

            <div className={styles.quickLoginSection}>
              <div className={styles.quickLoginTitle}>Quick Demo Sign-In</div>
              <div className={styles.quickLoginGrid}>
                <button
                  type="button"
                  className={styles.quickLoginBtn}
                  onClick={() => handleQuickLogin('student_alex')}
                  disabled={isSubmitting}
                >
                  <span className={styles.quickLoginName}>Alex Rivera</span>
                  <span className={styles.quickLoginRole}>Student (Junior CS)</span>
                </button>

                <button
                  type="button"
                  className={styles.quickLoginBtn}
                  onClick={() => handleQuickLogin('advisor_alice')}
                  disabled={isSubmitting}
                >
                  <span className={styles.quickLoginName}>Dr. Alice Chen</span>
                  <span className={styles.quickLoginRole}>Faculty Advisor</span>
                </button>

                <button
                  type="button"
                  className={styles.quickLoginBtn}
                  onClick={() => handleQuickLogin('coordinator_cora')}
                  disabled={isSubmitting}
                >
                  <span className={styles.quickLoginName}>Dr. Cora Vance</span>
                  <span className={styles.quickLoginRole}>Coordinator</span>
                </button>

                <button
                  type="button"
                  className={styles.quickLoginBtn}
                  onClick={() => handleQuickLogin('student_elena')}
                  disabled={isSubmitting}
                >
                  <span className={styles.quickLoginName}>Elena Rostova</span>
                  <span className={styles.quickLoginRole}>Honors Senior</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
