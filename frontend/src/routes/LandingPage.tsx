import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, Calendar, CheckCircle2, Shield, Users } from 'lucide-react';
import styles from './LandingPage.module.css';
import { Button } from '../components/Button/Button';
import { Input } from '../components/Input/Input';
import { Badge } from '../components/Badge/Badge';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('advisor@institution.edu');
  const [password, setPassword] = useState('••••••••••••');

  const handleSignIn = (e: React.FormEvent) => {
    e.preventDefault();
    // Navigates directly to the authenticated shell demo
    navigate('/dashboard');
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

            <form onSubmit={handleSignIn} className={styles.authForm}>
              <Input
                label="Institutional Email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
              <Input
                label="Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />

              <div className={styles.authNote}>
                <CheckCircle2 size={14} className={styles.noteIcon} />
                <span>Phase 01 prototype: Demo session enabled.</span>
              </div>

              <Button type="submit" variant="primary" size="md" className={styles.submitButton}>
                Enter Academic Workspace
              </Button>
            </form>
          </div>
        </div>
      </section>
    </div>
  );
};
