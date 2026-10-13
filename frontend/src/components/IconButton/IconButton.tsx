import React from 'react';
import styles from './IconButton.module.css';

export interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  'aria-label': string;
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  icon: React.ReactNode;
}

export const IconButton: React.FC<IconButtonProps> = ({
  'aria-label': ariaLabel,
  variant = 'ghost',
  size = 'md',
  icon,
  disabled,
  className = '',
  ...props
}) => {
  const buttonClasses = [
    styles.iconButton,
    styles[variant],
    styles[size],
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <button
      className={buttonClasses}
      disabled={disabled}
      aria-label={ariaLabel}
      title={ariaLabel}
      {...props}
    >
      <span className={styles.icon}>{icon}</span>
    </button>
  );
};
