import React from 'react';
import { PlanSimulationReport, PlanStatus } from '../../api/planning';
import styles from './PlanSimulationPanel.module.css';

export interface PlanSimulationPanelProps {
  simulation: PlanSimulationReport | null;
  planStatus: PlanStatus;
  isSimulating: boolean;
  onSimulate: () => void;
  onSubmitPlan: () => void;
  onOpenWhatIf: () => void;
  onOpenVersions: () => void;
  isReadOnly?: boolean;
}

export const PlanSimulationPanel: React.FC<PlanSimulationPanelProps> = ({
  simulation,
  planStatus,
  isSimulating,
  onSimulate,
  onSubmitPlan,
  onOpenWhatIf,
  onOpenVersions,
  isReadOnly = false,
}) => {
  const hasHardConstraints = Boolean(
    simulation && simulation.hard_constraints && simulation.hard_constraints.length > 0
  );
  const hasWarnings = Boolean(
    simulation && simulation.warnings && simulation.warnings.length > 0
  );
  const isValid = Boolean(simulation && simulation.is_valid_for_submission);

  const isSubmitted = planStatus === 'SUBMITTED';

  return (
    <div className={styles.panelContainer} data-testid="plan-simulation-panel">
      <div className={styles.topRow}>
        <div className={styles.timelineSection}>
          <div className={styles.gradBadge} data-testid="projected-grad-badge">
            <span className={styles.gradIcon}>🎓</span>
            <span>
              {simulation?.projected_graduation_term
                ? `Projected Graduation: ${simulation.projected_graduation_term}`
                : 'Graduation Timeline Pending'}
            </span>
          </div>

          <div className={styles.metricsRow}>
            <div className={styles.metricItem}>
              <span className={styles.metricLabel}>Planned Credits</span>
              <span className={styles.metricValue} data-testid="total-planned-credits">
                {simulation ? Number(simulation.total_planned_credits).toFixed(1) : '0.0'}
              </span>
            </div>
            <div className={styles.metricItem}>
              <span className={styles.metricLabel}>Cumulative Credits</span>
              <span className={styles.metricValue} data-testid="total-cumulative-credits">
                {simulation ? Number(simulation.total_cumulative_credits).toFixed(1) : '0.0'}
              </span>
            </div>
          </div>
        </div>

        <div className={styles.actionsSection}>
          <button
            type="button"
            className={`${styles.actionBtn} ${styles.btnSecondary}`}
            onClick={onSimulate}
            disabled={isSimulating}
            data-testid="simulate-plan-btn"
          >
            {isSimulating ? 'Simulating...' : '🔄 Run Simulation'}
          </button>

          <button
            type="button"
            className={`${styles.actionBtn} ${styles.btnSecondary}`}
            onClick={onOpenWhatIf}
            data-testid="what-if-btn"
          >
            🔮 What-If Analysis
          </button>

          <button
            type="button"
            className={`${styles.actionBtn} ${styles.btnSecondary}`}
            onClick={onOpenVersions}
            data-testid="version-history-btn"
          >
            📜 Snapshots & Diffs
          </button>

          {!isReadOnly && (
            <button
              type="button"
              className={`${styles.actionBtn} ${styles.btnSubmit}`}
              onClick={onSubmitPlan}
              disabled={!isValid || isSubmitted}
              title={
                isSubmitted
                  ? 'Plan is already submitted'
                  : hasHardConstraints
                  ? 'Resolve hard constraints before submitting'
                  : 'Submit plan for advisor review'
              }
              data-testid="submit-plan-btn"
            >
              {isSubmitted ? '✓ Submitted' : 'Submit for Advisor Review'}
            </button>
          )}
        </div>
      </div>

      {simulation?.graduation_projection_reason && (
        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-slate-700)' }}>
          <strong>Projection Status:</strong> {simulation.graduation_projection_reason}
        </div>
      )}

      {/* Constraints & Feedback Alerts */}
      <div className={styles.issuesContainer}>
        {hasHardConstraints && (
          <div className={styles.hardBanner} data-testid="hard-constraints-banner">
            <div className={styles.bannerTitle}>
              <span>⛔</span>
              <span>
                Submission Blocked: {simulation?.hard_constraints.length} Hard Constraint
                {simulation?.hard_constraints.length === 1 ? '' : 's'}
              </span>
            </div>
            <p style={{ margin: '0 0 var(--space-2) 0', fontSize: 'var(--font-size-xs)' }}>
              These errors violate degree prerequisites or maximum term limits and must be corrected
              before your plan can be submitted for official approval.
            </p>
            <ul className={styles.constraintList}>
              {simulation?.hard_constraints.map((c, i) => (
                <li key={i} className={styles.constraintItem} data-testid="hard-constraint-item">
                  <strong>[{c.code}]</strong> {c.message}
                </li>
              ))}
            </ul>
          </div>
        )}

        {hasWarnings && (
          <div className={styles.warningBanner} data-testid="warnings-banner">
            <div className={styles.bannerTitle}>
              <span>⚠️</span>
              <span>
                Advisory Warnings: {simulation?.warnings.length} Issue
                {simulation?.warnings.length === 1 ? '' : 's'}
              </span>
            </div>
            <ul className={styles.constraintList}>
              {simulation?.warnings.map((w, i) => (
                <li key={i} className={styles.constraintItem} data-testid="warning-item">
                  <strong>[{w.code}]</strong> {w.message}
                </li>
              ))}
            </ul>
          </div>
        )}

        {isValid && !hasHardConstraints && !hasWarnings && (
          <div className={styles.validBanner} data-testid="valid-plan-banner">
            <span>✓</span>
            <span>All degree prerequisites and term credit limits are fully satisfied.</span>
          </div>
        )}
      </div>
    </div>
  );
};
