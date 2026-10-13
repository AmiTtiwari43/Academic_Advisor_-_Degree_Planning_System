import React from 'react';
import { ChevronRight } from 'lucide-react';
import styles from './Breadcrumbs.module.css';

export interface BreadcrumbItem {
  label: string;
  href?: string;
  onClick?: () => void;
}

export interface BreadcrumbsProps {
  items: BreadcrumbItem[];
  className?: string;
}

export const Breadcrumbs: React.FC<BreadcrumbsProps> = ({ items, className = '' }) => {
  return (
    <nav aria-label="Breadcrumb" className={`${styles.nav} ${className}`}>
      <ol className={styles.list}>
        {items.map((item, index) => {
          const isLast = index === items.length - 1;

          return (
            <li key={index} className={styles.item}>
              {index > 0 && <ChevronRight size={14} className={styles.separator} aria-hidden="true" />}
              {isLast || (!item.href && !item.onClick) ? (
                <span className={styles.current} aria-current={isLast ? 'page' : undefined}>
                  {item.label}
                </span>
              ) : item.href ? (
                <a href={item.href} className={styles.link}>
                  {item.label}
                </a>
              ) : (
                <button type="button" onClick={item.onClick} className={styles.buttonLink}>
                  {item.label}
                </button>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
};
