import React from 'react';
import styles from './Badge.module.css';

export interface BadgeProps {
  children: React.ReactNode;
  variant?: 'neutral' | 'success' | 'warning' | 'danger' | 'info' | 'teal';
  size?: 'sm' | 'md';
  icon?: React.ReactNode;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  size = 'md',
  icon,
  className = '',
}) => {
  return (
    <span
      className={[
        styles.badge,
        styles[variant],
        styles[size],
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {icon && <span className={styles.icon}>{icon}</span>}
      <span className={styles.label}>{children}</span>
    </span>
  );
};
