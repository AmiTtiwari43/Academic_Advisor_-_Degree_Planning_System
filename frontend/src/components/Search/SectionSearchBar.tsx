import React from 'react';
import { Search, X } from 'lucide-react';
import styles from './SectionSearchBar.module.css';

export interface SectionSearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  badgeCount?: number;
  className?: string;
  id?: string;
  'aria-label'?: string;
}

export const SectionSearchBar: React.FC<SectionSearchBarProps> = ({
  value,
  onChange,
  placeholder = 'Filter records by keyword, code, or registration number...',
  badgeCount,
  className = '',
  id,
  'aria-label': ariaLabel = 'Search section records',
}) => {
  return (
    <div className={`${styles.container} ${className}`}>
      <div className={styles.searchWrapper}>
        <Search size={16} className={styles.searchIcon} />
        <input
          type="text"
          id={id}
          className={styles.searchInput}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          aria-label={ariaLabel}
        />
        {value && (
          <button
            type="button"
            className={styles.clearButton}
            onClick={() => onChange('')}
            aria-label="Clear search"
          >
            <X size={14} />
          </button>
        )}
      </div>
      {typeof badgeCount === 'number' && (
        <span className={styles.badge}>
          {badgeCount} {badgeCount === 1 ? 'record' : 'records'}
        </span>
      )}
    </div>
  );
};
