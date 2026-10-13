import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import styles from './ErrorState.module.css';
import { Button } from '../Button/Button';

export interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  action?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Unable to Load Academic Data',
  message = 'An unexpected server error occurred while retrieving this record. Please verify your connection or try again.',
  onRetry,
  action,
  children,
  className = '',
}) => {
  return (
    <div className={`${styles.errorState} ${className}`} role="alert">
      <div className={styles.iconContainer}>
        <AlertTriangle size={32} className={styles.alertIcon} />
      </div>
      <h3 className={styles.title}>{title}</h3>
      <p className={styles.message}>{message}</p>
      {onRetry && (
        <Button
          variant="outline"
          size="sm"
          leftIcon={<RefreshCw size={14} />}
          onClick={onRetry}
        >
          Retry Request
        </Button>
      )}
      {action && <div style={{ marginTop: 'var(--space-4)' }}>{action}</div>}
      {children}
    </div>
  );
};
