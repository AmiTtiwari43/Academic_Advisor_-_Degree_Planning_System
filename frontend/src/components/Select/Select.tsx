import React, { useId } from 'react';
import styles from './Select.module.css';

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  helperText?: string;
  errorMessage?: string;
  options: SelectOption[];
}

export const Select: React.FC<SelectProps> = ({
  label,
  helperText,
  errorMessage,
  options,
  id: customId,
  disabled,
  className = '',
  ...props
}) => {
  const generatedId = useId();
  const selectId = customId || generatedId;
  const errorId = `${selectId}-error`;
  const helperId = `${selectId}-helper`;

  return (
    <div className={`${styles.container} ${className}`}>
      {label && (
        <label htmlFor={selectId} className={styles.label}>
          {label}
        </label>
      )}
      <div
        className={[
          styles.selectWrapper,
          errorMessage ? styles.hasError : '',
          disabled ? styles.disabled : '',
        ]
          .filter(Boolean)
          .join(' ')}
      >
        <select
          id={selectId}
          className={styles.select}
          disabled={disabled}
          aria-invalid={Boolean(errorMessage)}
          aria-describedby={errorMessage ? errorId : helperText ? helperId : undefined}
          {...props}
        >
          {options.map((option) => (
            <option
              key={option.value}
              value={option.value}
              disabled={option.disabled}
            >
              {option.label}
            </option>
          ))}
        </select>
        <span className={styles.arrow} aria-hidden="true">
          ▼
        </span>
      </div>
      {errorMessage ? (
        <p id={errorId} className={styles.errorText} role="alert">
          {errorMessage}
        </p>
      ) : helperText ? (
        <p id={helperId} className={styles.helperText}>
          {helperText}
        </p>
      ) : null}
    </div>
  );
};
