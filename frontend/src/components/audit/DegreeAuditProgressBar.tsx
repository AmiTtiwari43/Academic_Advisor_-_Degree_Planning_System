import React from 'react';
import styles from './DegreeAuditProgressBar.module.css';

interface DegreeAuditProgressBarProps {
  totalRequired: number;
  totalEarned: number;
  totalInProgress: number;
  remainingRequired: number;
  cgpa: number;
  minCgpa: number;
  isDegreeSatisfied: boolean;
}

export const DegreeAuditProgressBar: React.FC<DegreeAuditProgressBarProps> = ({
  totalRequired,
  totalEarned,
  totalInProgress,
  remainingRequired,
  cgpa,
  minCgpa,
  isDegreeSatisfied,
}) => {
  const earnedPct = totalRequired > 0 ? Math.min(100, Math.round((totalEarned / totalRequired) * 100)) : 100;
  const inProgressPct = totalRequired > 0 ? Math.min(100 - earnedPct, Math.round((totalInProgress / totalRequired) * 100)) : 0;
  const cgpaSatisfied = Number(cgpa) >= Number(minCgpa);

  return (
    <div className={styles.progressContainer} data-testid="degree-audit-progress-card">
      <div className={styles.topRow}>
        <div className={styles.metricGroup}>
          <span className={styles.label}>Degree Progress</span>
          <div className={styles.valueRow}>
            <span className={styles.mainValue} data-testid="audit-earned-credits">{totalEarned}</span>
            <span className={styles.subValue}>/ {totalRequired} Credits Required</span>
            {totalInProgress > 0 && (
              <span className={styles.inProgressBadge} data-testid="audit-inprogress-credits">
                +{totalInProgress} in progress
              </span>
            )}
          </div>
        </div>

        <div className={styles.cgpaGroup}>
          <span className={styles.label}>Cumulative GPA</span>
          <div className={styles.valueRow}>
            <span className={styles.mainValue} data-testid="audit-cgpa">{Number(cgpa).toFixed(2)}</span>
            <span className={styles.subValue}>/ {Number(minCgpa).toFixed(2)} Min Required</span>
            <span
              className={cgpaSatisfied ? styles.cgpaBadgeSuccess : styles.cgpaBadgeDanger}
              data-testid="audit-cgpa-status"
            >
              {cgpaSatisfied ? 'Satisfied' : 'Below Threshold'}
            </span>
          </div>
        </div>

        <div className={styles.statusGroup}>
          <span className={styles.label}>Overall Audit Status</span>
          <div className={styles.statusBadgeWrapper}>
            <span
              className={isDegreeSatisfied ? styles.statusSatisfied : styles.statusPending}
              data-testid="audit-overall-status"
            >
              {isDegreeSatisfied ? 'ALL REQUIREMENTS SATISFIED' : `${remainingRequired} CREDITS REMAINING`}
            </span>
          </div>
        </div>
      </div>

      <div className={styles.barWrapper}>
        <div
          className={styles.progressBar}
          role="progressbar"
          aria-valuenow={earnedPct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Degree progress percentage"
        >
          <div
            className={styles.earnedSegment}
            style={{ width: `${earnedPct}%` }}
            title={`Earned: ${totalEarned} credits (${earnedPct}%)`}
          />
          <div
            className={styles.inProgressSegment}
            style={{ width: `${inProgressPct}%` }}
            title={`In Progress: ${totalInProgress} credits (${inProgressPct}%)`}
          />
        </div>
        <div className={styles.legend}>
          <span className={styles.legendItem}>
            <span className={styles.legendDotEarned} /> Earned ({earnedPct}%)
          </span>
          {totalInProgress > 0 && (
            <span className={styles.legendItem}>
              <span className={styles.legendDotInProgress} /> In-Progress ({inProgressPct}%)
            </span>
          )}
          <span className={styles.legendItem}>
            <span className={styles.legendDotRemaining} /> Remaining ({Math.max(0, 100 - earnedPct - inProgressPct)}%)
          </span>
        </div>
      </div>
    </div>
  );
};
