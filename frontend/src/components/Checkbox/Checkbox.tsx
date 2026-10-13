import React, { useId } from 'react';
import styles from './Checkbox.module.css';

export interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label: string;
  description?: string;
}

export const Checkbox: React.FC<CheckboxProps> = ({
  label,
  description,
  id: customId,
  disabled,
  className = '',
  ...props
}) => {
  const generatedId = useId();
  const checkboxId = customId || generatedId;

  return (
    <div className={`${styles.wrapper} ${disabled ? styles.disabled : ''} ${className}`}>
      <label htmlFor={checkboxId} className={styles.labelContainer}>
        <input
          type="checkbox"
          id={checkboxId}
          className={styles.input}
          disabled={disabled}
          {...props}
        />
        <span className={styles.customBox} aria-hidden="true">
          <svg viewBox="0 0 16 16" fill="currentColor" className={styles.checkIcon}>
            <path d="M12.207 4.793a1 1 0 010 1.414l-5 5a1 1 0 01-1.414 0l-2-2a1 1 0 011.414-1.414L6.5 9.086l4.293-4.293a1 1 0 011.414 0z" />
          </svg>
        </span>
        <span className={styles.textContainer}>
          <span className={styles.labelText}>{label}</span>
          {description && <span className={styles.description}>{description}</span>}
        </span>
      </label>
    </div>
  );
};
