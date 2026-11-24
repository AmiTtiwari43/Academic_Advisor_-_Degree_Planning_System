import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ShieldAlert, ArrowLeft } from 'lucide-react';
import { Button } from '../components';
import { useAuth } from '../context/AuthContext';
import styles from './NotFoundPage.module.css';

export const AccessDeniedPage: React.FC = () => {
  const location = useLocation();
  const { roleDisplayName, unifiedRole } = useAuth();
  const state = location.state as {
    deniedPath?: string;
    requiredRoles?: string[];
    currentRole?: string;
  } | null;

  const currentRoleName = roleDisplayName || state?.currentRole || unifiedRole;

  return (
    <div className={styles.container}>
      <div className={styles.content}>
        <div style={{ textAlign: 'center', maxWidth: '540px', margin: '0 auto', padding: '2.5rem 1.5rem' }}>
          <div
            style={{
              width: '64px',
              height: '64px',
              borderRadius: '16px',
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              color: '#DC2626',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 1.5rem',
            }}
          >
            <ShieldAlert size={36} />
          </div>

          <span
            style={{
              display: 'inline-block',
              padding: '4px 12px',
              borderRadius: '999px',
              fontSize: '0.78rem',
              fontWeight: 700,
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              backgroundColor: '#FEE2E2',
              color: '#991B1B',
              marginBottom: '0.75rem',
            }}
          >
            RBAC Authorization Restricted
          </span>

          <h1 style={{ fontSize: '1.85rem', fontWeight: 700, color: '#0F172A', marginBottom: '0.75rem' }}>
            403 — Access Denied
          </h1>

          <p style={{ fontSize: '0.95rem', color: '#64748B', lineHeight: 1.6, marginBottom: '1.5rem' }}>
            Your account is assigned the role of <strong>{currentRoleName}</strong>. You only have access to your specified tasks and panels in accordance with strict institutional role-based access control.
          </p>

          {state?.deniedPath && (
            <div
              style={{
                backgroundColor: '#F8FAFC',
                border: '1px solid #E2E8F0',
                borderRadius: '8px',
                padding: '0.85rem 1rem',
                marginBottom: '1.75rem',
                fontSize: '0.85rem',
                color: '#475569',
                textAlign: 'left',
              }}
            >
              <div><strong>Attempted Route:</strong> <code>{state.deniedPath}</code></div>
              {state.requiredRoles && (
                <div style={{ marginTop: '4px' }}>
                  <strong>Authorized Roles:</strong> {state.requiredRoles.map((r) => r.charAt(0) + r.slice(1).toLowerCase()).join(', ')}
                </div>
              )}
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem' }}>
            <Link to="/dashboard" style={{ textDecoration: 'none' }}>
              <Button variant="primary" leftIcon={<ArrowLeft size={16} />}>
                Return to Dashboard
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
