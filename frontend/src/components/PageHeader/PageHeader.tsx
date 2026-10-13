import React from 'react';
import styles from './PageHeader.module.css';
import { Breadcrumbs, BreadcrumbItem } from '../Breadcrumbs/Breadcrumbs';

export interface PageHeaderProps {
  title: string;
  subtitle?: string;
  badge?: React.ReactNode;
  breadcrumbs?: BreadcrumbItem[];
  actions?: React.ReactNode;
  className?: string;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  subtitle,
  badge,
  breadcrumbs,
  actions,
  className = '',
}) => {
  return (
    <div className={`${styles.header} ${className}`}>
      {breadcrumbs && breadcrumbs.length > 0 && (
        <div className={styles.breadcrumbsWrapper}>
          <Breadcrumbs items={breadcrumbs} />
        </div>
      )}
      <div className={styles.contentRow}>
        <div className={styles.titleArea}>
          <div className={styles.titleRow}>
            <h1 className={styles.title}>{title}</h1>
            {badge && <div className={styles.badgeWrapper}>{badge}</div>}
          </div>
          {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
        </div>
        {actions && <div className={styles.actions}>{actions}</div>}
      </div>
    </div>
  );
};
