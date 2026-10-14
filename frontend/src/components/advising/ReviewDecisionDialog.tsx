import React, { useState, useEffect } from 'react';
import styles from './ReviewDecisionDialog.module.css';

export interface DecisionSubmitData {
  comments: string;
  idempotency_key: string;
}

interface ReviewDecisionDialogProps {
  isOpen: boolean;
  action: 'APPROVE' | 'RETURN' | 'REJECT' | null;
  planName: string;
  versionNumber: number;
  rowVersion: number;
  onClose: () => void;
  onConfirm: (data: DecisionSubmitData) => void;
  isLoading: boolean;
}

export const ReviewDecisionDialog: React.FC<ReviewDecisionDialogProps> = ({
  isOpen,
  action,
  planName,
  versionNumber,
  rowVersion,
  onClose,
  onConfirm,
  isLoading,
}) => {
  const [comments, setComments] = useState('');
  const [idempotencyKey, setIdempotencyKey] = useState('');

  useEffect(() => {
    if (isOpen) {
      setComments('');
      // Generate unique idempotency key for this review action
      const newKey =
        typeof crypto !== 'undefined' && crypto.randomUUID
          ? crypto.randomUUID()
          : `key-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
      setIdempotencyKey(newKey);
    }
  }, [isOpen, action]);

  if (!isOpen || !action) return null;

  const isReturnOrReject = action === 'RETURN' || action === 'REJECT';
  const isCommentsValid = !isReturnOrReject || comments.trim().length > 0;

  const getActionTitle = () => {
    switch (action) {
      case 'APPROVE':
        return `Approve Plan — Version ${versionNumber}`;
      case 'RETURN':
        return `Return Plan for Student Revision`;
      case 'REJECT':
        return `Reject Plan Submission`;
      default:
        return 'Review Decision';
    }
  };

  const getConfirmButtonTheme = () => {
    switch (action) {
      case 'APPROVE':
        return styles.approveTheme;
      case 'RETURN':
        return styles.returnTheme;
      case 'REJECT':
        return styles.rejectTheme;
      default:
        return '';
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isCommentsValid || isLoading) return;
    onConfirm({ comments: comments.trim(), idempotency_key: idempotencyKey });
  };

  return (
    <div className={styles.overlay} role="dialog" aria-modal="true">
      <div className={styles.modal}>
        <div className={styles.header}>
          <h3 className={styles.title}>{getActionTitle()}</h3>
          <button className={styles.closeBtn} onClick={onClose} disabled={isLoading}>
            &times;
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className={styles.body}>
            <div className={styles.callout}>
              <strong>Plan:</strong> {planName} (v{versionNumber}) &bull;{' '}
              <strong>Optimistic Lock:</strong> #{rowVersion}
            </div>

            <div className={styles.fieldGroup}>
              <label className={styles.label}>
                {isReturnOrReject ? 'Feedback Comments (Required):' : 'Advisor Notes (Optional):'}
              </label>
              <textarea
                className={styles.textarea}
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                placeholder={
                  isReturnOrReject
                    ? 'Explain the required changes, term rebalancing, or missing prerequisites...'
                    : 'Notes on approval or recommendations for upcoming registration...'
                }
                rows={4}
                required={isReturnOrReject}
              />
              <span className={styles.helpText}>
                {isReturnOrReject
                  ? 'Your comments will be displayed to the student in their planner and audit log.'
                  : 'Optional notes recorded in the permanent degree plan review decision log.'}
              </span>
            </div>
          </div>

          <div className={styles.footer}>
            <button
              type="button"
              className={styles.btnCancel}
              onClick={onClose}
              disabled={isLoading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className={`${styles.btnConfirm} ${getConfirmButtonTheme()}`}
              disabled={!isCommentsValid || isLoading}
            >
              {isLoading
                ? 'Processing...'
                : action === 'APPROVE'
                ? 'Confirm Approval'
                : action === 'RETURN'
                ? 'Return for Revision'
                : 'Confirm Rejection'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
