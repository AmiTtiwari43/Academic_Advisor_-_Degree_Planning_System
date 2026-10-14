import React from 'react';
import { Plan, PlanVersion } from '../../api/planning';
import { Badge } from '../Badge/Badge';
import styles from './ReviewActionBar.module.css';

interface ReviewActionBarProps {
  plan: Plan;
  latestVersion: PlanVersion | null;
  onStartReview: () => void;
  onOpenDecisionDialog: (action: 'APPROVE' | 'RETURN' | 'REJECT') => void;
  onOpenOverrideModal: () => void;
  isActionLoading: boolean;
}

export const ReviewActionBar: React.FC<ReviewActionBarProps> = ({
  plan,
  latestVersion,
  onStartReview,
  onOpenDecisionDialog,
  onOpenOverrideModal,
  isActionLoading,
}) => {
  const isSubmittedOrResubmitted =
    plan.status === 'SUBMITTED' || plan.status === 'RESUBMITTED';
  const isUnderReview = plan.status === 'UNDER_REVIEW';

  const getStatusBadgeVariant = (
    status: string
  ): 'neutral' | 'success' | 'warning' | 'danger' | 'info' => {
    switch (status) {
      case 'APPROVED':
        return 'success';
      case 'SUBMITTED':
      case 'RESUBMITTED':
        return 'info';
      case 'UNDER_REVIEW':
      case 'RETURNED':
        return 'warning';
      case 'REJECTED':
        return 'danger';
      default:
        return 'neutral';
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.planContext}>
        <span className={styles.planTitle}>{plan.name}</span>
        <Badge variant={getStatusBadgeVariant(plan.status)}>{plan.status}</Badge>
        {latestVersion && (
          <span className={styles.metaBadge}>Version {latestVersion.version_number}</span>
        )}
        <span className={styles.metaBadge}>OCC #{plan.row_version}</span>
      </div>

      <div className={styles.actionsGroup}>
        {isSubmittedOrResubmitted && (
          <button
            className={`${styles.btnAction} ${styles.btnStartReview}`}
            onClick={onStartReview}
            disabled={isActionLoading}
          >
            Start Official Review
          </button>
        )}

        {isUnderReview && (
          <>
            <button
              className={`${styles.btnAction} ${styles.btnApprove}`}
              onClick={() => onOpenDecisionDialog('APPROVE')}
              disabled={isActionLoading}
            >
              Approve Plan
            </button>
            <button
              className={`${styles.btnAction} ${styles.btnReturn}`}
              onClick={() => onOpenDecisionDialog('RETURN')}
              disabled={isActionLoading}
            >
              Return for Revision
            </button>
            <button
              className={`${styles.btnAction} ${styles.btnReject}`}
              onClick={() => onOpenDecisionDialog('REJECT')}
              disabled={isActionLoading}
            >
              Reject Plan
            </button>
          </>
        )}

        <button
          className={`${styles.btnAction} ${styles.btnOverride}`}
          onClick={onOpenOverrideModal}
          disabled={isActionLoading}
        >
          Record Override
        </button>
      </div>
    </div>
  );
};
