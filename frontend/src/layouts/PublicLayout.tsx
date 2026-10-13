import React from 'react';
import { Outlet, Link } from 'react-router-dom';
import { GraduationCap, Shield } from 'lucide-react';
import styles from './PublicLayout.module.css';

export const PublicLayout: React.FC = () => {
  return (
    <div className={styles.publicShell}>
      {/* Editorial Header */}
      <header className={styles.header}>
        <div className={styles.headerContainer}>
          <Link to="/" className={styles.brand}>
            <div className={styles.logoBadge}>
              <GraduationCap size={22} className={styles.brandIcon} />
            </div>
            <div className={styles.brandText}>
              <span className={styles.brandTitle}>Academic Advisor</span>
              <span className={styles.brandSubtitle}>Degree Planning Platform</span>
            </div>
          </Link>

          <nav className={styles.nav}>
            <Link to="/dashboard" className={styles.navLink}>
              Live Demo Workspace
            </Link>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className={styles.main}>
        <Outlet />
      </main>

      {/* Footer */}
      <footer className={styles.footer}>
        <div className={styles.footerContainer}>
          <div className={styles.footerLeft}>
            <Shield size={16} className={styles.shieldIcon} />
            <span>Academic Rules Engine &copy; 2026. Institutional Multi-Tenancy Architecture.</span>
          </div>
          <div className={styles.footerRight}>
            <span>Modular Monolith &bull; Django 5.x &bull; PostgreSQL JSONB</span>
          </div>
        </div>
      </footer>
    </div>
  );
};
