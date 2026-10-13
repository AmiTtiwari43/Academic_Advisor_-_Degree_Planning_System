import React, { useEffect } from 'react';
import { X } from 'lucide-react';
import styles from './Dialog.module.css';
import { IconButton } from '../IconButton/IconButton';

export interface DialogProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  maxWidth?: 'sm' | 'md' | 'lg';
}

export const Dialog: React.FC<DialogProps> = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  footer,
  maxWidth = 'md',
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={onClose} role="presentation">
      <div
        className={`${styles.dialog} ${styles[maxWidth]}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
        aria-describedby={description ? 'dialog-description' : undefined}
        onClick={(e) => e.stopPropagation()}
      >
        <div className={styles.header}>
          <div>
            <h2 id="dialog-title" className={styles.title}>
              {title}
            </h2>
            {description && (
              <p id="dialog-description" className={styles.description}>
                {description}
              </p>
            )}
          </div>
          <IconButton
            icon={<X size={18} />}
            aria-label="Close dialog"
            onClick={onClose}
            size="sm"
          />
        </div>
        <div className={styles.body}>{children}</div>
        {footer && <div className={styles.footer}>{footer}</div>}
      </div>
    </div>
  );
};
