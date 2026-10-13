import React, { useId } from 'react';
import styles from './Input.module.css';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  helperText?: string;
  errorMessage?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Input: React.FC<InputProps> = ({
  label,
  helperText,
  errorMessage,
  leftIcon,
  rightIcon,
  id: customId,
  disabled,
  className = '',
  ...props
}) => {
  const generatedId = useId();
  const inputId = customId || generatedId;
  const errorId = `${inputId}-error`;
  const helperId = `${inputId}-helper`;

  return (
    <div className={`${styles.container} ${className}`}>
      {label && (
        <label htmlFor={inputId} className={styles.label}>
          {label}
        </label>
      )}
      <div
        className={[
          styles.inputWrapper,
          errorMessage ? styles.hasError : '',
          disabled ? styles.disabled : '',
        ]
          .filter(Boolean)
          .join(' ')}
      >
        {leftIcon && <span className={styles.icon}>{leftIcon}</span>}
        <input
          id={inputId}
          className={styles.input}
          disabled={disabled}
          aria-invalid={Boolean(errorMessage)}
          aria-describedby={errorMessage ? errorId : helperText ? helperId : undefined}
          {...props}
        />
        {rightIcon && <span className={styles.icon}>{rightIcon}</span>}
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
