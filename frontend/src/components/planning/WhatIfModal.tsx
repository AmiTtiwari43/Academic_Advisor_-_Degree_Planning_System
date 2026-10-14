import React, { useEffect, useState } from 'react';
import { PlanAuditGroupSummary, PlanSimulationReport, planningApi } from '../../api/planning';
import { Programme, curriculumApi } from '../../api/curriculum';
import styles from './WhatIfModal.module.css';

export interface WhatIfModalProps {
  studentRecordId: string;
  planId?: string;
  isOpen: boolean;
  onClose: () => void;
}

export const WhatIfModal: React.FC<WhatIfModalProps> = ({
  studentRecordId,
  planId,
  isOpen,
  onClose,
}) => {
  const [programmes, setProgrammes] = useState<Programme[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState<string>('');
  const [loadingProgrammes, setLoadingProgrammes] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const [simulationResult, setSimulationResult] = useState<PlanSimulationReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    setLoadingProgrammes(true);
    setError(null);
    setSimulationResult(null);

    curriculumApi
      .getProgrammes()
      .then((data) => {
        setProgrammes(data);
        // Find first published version
        for (const prog of data) {
          const pub = prog.curriculum_versions?.find((v) => v.status === 'PUBLISHED');
          if (pub) {
            setSelectedVersionId(pub.id);
            break;
          }
        }
      })
      .catch((err) => {
        setError(err.message || 'Failed to fetch academic programmes.');
      })
      .finally(() => {
        setLoadingProgrammes(false);
      });
  }, [isOpen]);

  const handleRunWhatIf = () => {
    if (!selectedVersionId || !studentRecordId) return;

    setSimulating(true);
    setError(null);

    planningApi
      .simulateWhatIf({
        student_record_id: studentRecordId,
        target_curriculum_version_id: selectedVersionId,
        plan_id: planId,
      })
      .then((res) => {
        setSimulationResult(res);
      })
      .catch((err) => {
        setError(err.message || 'Failed to execute What-If simulation.');
      })
      .finally(() => {
        setSimulating(false);
      });
  };

  if (!isOpen) return null;

  return (
    <div
      className={styles.modalBackdrop}
      role="dialog"
      aria-modal="true"
      aria-labelledby="what-if-dialog-title"
      data-testid="what-if-modal"
    >
      <div className={styles.modalContent}>
        <header className={styles.modalHeader}>
          <h2 id="what-if-dialog-title" className={styles.modalTitle}>
            What-If Scenario Simulation
          </h2>
          <button
            type="button"
            className={styles.closeBtn}
            onClick={onClose}
            aria-label="Close modal"
            data-testid="close-what-if-btn"
          >
            ✕
          </button>
        </header>

        <div className={styles.modalBody}>
          <div className={styles.disclaimerBanner} data-testid="what-if-disclaimer">
            <span>🛡️</span>
            <span>
              <strong>Simulation Mode:</strong> This analysis simulates degree requirements
              against an alternative curriculum version. No official student records or degree plans
              are modified.
            </span>
          </div>

          {loadingProgrammes ? (
            <p style={{ textAlign: 'center', padding: 'var(--space-4)' }}>
              Loading curriculum options...
            </p>
          ) : (
            <div className={styles.selectionRow}>
              <label htmlFor="target-curriculum-select" className={styles.selectLabel}>
                Target Degree Programme & Curriculum:
              </label>
              <select
                id="target-curriculum-select"
                className={styles.selectInput}
                value={selectedVersionId}
                onChange={(e) => setSelectedVersionId(e.target.value)}
                data-testid="what-if-target-select"
              >
                {programmes.map((prog) => {
                  const versions = prog.curriculum_versions || [];
                  return (
                    <optgroup key={prog.id} label={`${prog.code} - ${prog.name}`}>
                      {versions.map((v) => (
                        <option key={v.id} value={v.id}>
                          {prog.code} v{v.version_number} ({v.academic_year}) - {v.status}
                        </option>
                      ))}
                    </optgroup>
                  );
                })}
              </select>

              <button
                type="button"
                className={styles.runBtn}
                onClick={handleRunWhatIf}
                disabled={!selectedVersionId || simulating}
                data-testid="run-what-if-btn"
              >
                {simulating ? 'Simulating Dry-Run...' : 'Run What-If Simulation'}
              </button>
            </div>
          )}

          {error && (
            <div style={{ color: 'var(--color-status-danger-text)', fontSize: 'var(--font-size-sm)' }}>
              {error}
            </div>
          )}

          {simulationResult && (
            <div className={styles.resultsContainer} data-testid="what-if-results">
              <div className={styles.metricCards}>
                <div className={styles.card}>
                  <div className={styles.cardLabel}>Projected Graduation</div>
                  <div className={styles.cardValue} data-testid="what-if-grad-term">
                    {simulationResult.projected_graduation_term || 'Unmet'}
                  </div>
                </div>

                <div className={styles.card}>
                  <div className={styles.cardLabel}>Total Cumulative Credits</div>
                  <div className={styles.cardValue}>
                    {Number(simulationResult.total_cumulative_credits).toFixed(1)} cr
                  </div>
                </div>

                <div className={styles.card}>
                  <div className={styles.cardLabel}>Hard Constraints</div>
                  <div
                    className={styles.cardValue}
                    style={{
                      color:
                        simulationResult.hard_constraints.length > 0
                          ? 'var(--color-status-danger-text)'
                          : 'var(--color-status-success-text)',
                    }}
                  >
                    {simulationResult.hard_constraints.length}
                  </div>
                </div>
              </div>

              {simulationResult.graduation_projection_reason && (
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-slate-700)' }}>
                  <strong>Projection Result:</strong> {simulationResult.graduation_projection_reason}
                </div>
              )}

              {/* Requirement Group Audit Breakdown */}
              {simulationResult.audit_report?.groups && (
                <div>
                  <h3 style={{ fontSize: 'var(--font-size-sm)', margin: 'var(--space-3) 0 var(--space-2) 0' }}>
                    Requirement Groups Breakdown
                  </h3>
                  <div className={styles.groupAuditList}>
                    {simulationResult.audit_report.groups.map((grp: PlanAuditGroupSummary, idx: number) => (
                      <div
                        key={idx}
                        className={`${styles.groupItem} ${
                          grp.is_satisfied ? styles.groupSatisfied : styles.groupUnsatisfied
                        }`}
                        data-testid="what-if-group-item"
                      >
                        <div>
                          <strong>{grp.name}</strong> ({grp.group_type})
                          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-slate-500)' }}>
                            Earned: {Number(grp.earned_credits).toFixed(1)} / {Number(grp.min_credits).toFixed(1)} cr
                          </div>
                        </div>
                        <span
                          style={{
                            fontWeight: 600,
                            color: grp.is_satisfied ? '#16A34A' : '#DC2626',
                          }}
                        >
                          {grp.is_satisfied ? '✓ Satisfied' : 'Pending'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
