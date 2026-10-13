import React, { useEffect } from 'react';
import { AlertCircle, CheckCircle2, Info, X } from 'lucide-react';
import styles from './Toast.module.css';

export interface ToastProps {
  id: string;
  type?: 'success' | 'warning' | 'danger' | 'info';
  title: string;
  message?: string;
  duration?: number;
  onClose: (id: string) => void;
}

export const Toast: React.FC<ToastProps> = ({
  id,
  type = 'info',
  title,
  message,
  duration = 5000,
  onClose,
}) => {
  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => onClose(id), duration);
      return () => clearTimeout(timer);
    }
  }, [id, duration, onClose]);

  const renderIcon = () => {
    switch (type) {
      case 'success':
        return <CheckCircle2 size={18} className={styles.successIcon} />;
      case 'warning':
        return <AlertCircle size={18} className={styles.warningIcon} />;
      case 'danger':
        return <AlertCircle size={18} className={styles.dangerIcon} />;
      case 'info':
      default:
        return <Info size={18} className={styles.infoIcon} />;
    }
  };

  return (
    <div className={`${styles.toast} ${styles[type]}`} role="alert">
      <div className={styles.iconContainer}>{renderIcon()}</div>
      <div className={styles.content}>
        <h4 className={styles.title}>{title}</h4>
        {message && <p className={styles.message}>{message}</p>}
      </div>
      <button
        type="button"
        className={styles.closeButton}
        onClick={() => onClose(id)}
        aria-label="Close notification"
      >
        <X size={14} />
      </button>
    </div>
  );
};
