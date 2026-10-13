import React from 'react';
import { Inbox } from 'lucide-react';
import styles from './EmptyState.module.css';

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
  className = '',
}) => {
  return (
    <div className={`${styles.emptyState} ${className}`}>
      <div className={styles.iconContainer}>
        {icon || <Inbox size={36} className={styles.defaultIcon} />}
      </div>
      <h3 className={styles.title}>{title}</h3>
      {description && <p className={styles.description}>{description}</p>}
      {action && <div className={styles.actionContainer}>{action}</div>}
    </div>
  );
};
