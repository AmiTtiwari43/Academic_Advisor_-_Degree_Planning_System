import React from 'react';
import { PlanAuditLog } from '../../api/advising';
import { Badge } from '../Badge/Badge';
import styles from './ReviewAuditTimeline.module.css';

interface ReviewAuditTimelineProps {
  logs: PlanAuditLog[];
  isLoading?: boolean;
}

export const ReviewAuditTimeline: React.FC<ReviewAuditTimelineProps> = ({
  logs,
  isLoading,
}) => {
  const getActionBadgeVariant = (
    action: string
  ): 'neutral' | 'success' | 'warning' | 'danger' | 'info' => {
    if (action.includes('APPROVE')) return 'success';
    if (action.includes('RETURN')) return 'warning';
    if (action.includes('REJECT')) return 'danger';
    if (action.includes('OVERRIDE')) return 'info';
    return 'neutral';
  };

  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className={styles.container}>
      <h4 className={styles.title}>Audit Log & Decision History</h4>

      {isLoading ? (
        <div className={styles.emptyMessage}>Loading audit trail...</div>
      ) : logs.length === 0 ? (
        <div className={styles.emptyMessage}>No transitions recorded yet.</div>
      ) : (
        <div className={styles.timeline}>
          {logs.map((log) => (
            <div key={log.id} className={styles.item}>
              <div className={styles.itemHeader}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className={styles.actionTitle}>{log.action}</span>
                  <Badge variant={getActionBadgeVariant(log.action)}>
                    {log.from_status ? `${log.from_status} → ${log.to_status}` : log.to_status}
                  </Badge>
                </div>
                <span className={styles.timestamp}>{formatDate(log.created_at)}</span>
              </div>

              <div className={styles.actorInfo}>
                By: <strong>{log.actor_username || 'System'}</strong>
                {log.version_number && ` • Version ${log.version_number}`}
              </div>

              {log.comment && <div className={styles.comment}>{log.comment}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
