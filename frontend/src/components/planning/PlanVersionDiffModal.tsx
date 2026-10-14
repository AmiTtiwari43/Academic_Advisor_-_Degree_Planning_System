import React, { useEffect, useState } from 'react';
import { PlanDiffReport, PlanVersion, planningApi } from '../../api/planning';
import styles from './PlanVersionDiffModal.module.css';

export interface PlanVersionDiffModalProps {
  planId: string;
  isOpen: boolean;
  onClose: () => void;
}

export const PlanVersionDiffModal: React.FC<PlanVersionDiffModalProps> = ({
  planId,
  isOpen,
  onClose,
}) => {
  const [versions, setVersions] = useState<PlanVersion[]>([]);
  const [selectedVA, setSelectedVA] = useState<number | null>(null);
  const [selectedVB, setSelectedVB] = useState<number | null>(null);
  const [diffReport, setDiffReport] = useState<PlanDiffReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [diffLoading, setDiffLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !planId) return;

    setLoading(true);
    setError(null);
    planningApi
      .fetchPlanVersions(planId)
      .then((data) => {
        setVersions(data);
        if (data.length >= 2) {
          const sorted = [...data].sort((a, b) => a.version_number - b.version_number);
          setSelectedVA(sorted[sorted.length - 2].version_number);
          setSelectedVB(sorted[sorted.length - 1].version_number);
        } else if (data.length === 1) {
          setSelectedVA(data[0].version_number);
          setSelectedVB(data[0].version_number);
        }
      })
      .catch((err) => {
        setError(err.message || 'Failed to fetch plan version history.');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [isOpen, planId]);

  useEffect(() => {
    if (selectedVA === null || selectedVB === null || !planId) return;

    setDiffLoading(true);
    setError(null);
    planningApi
      .comparePlanVersions(planId, selectedVA, selectedVB)
      .then((report) => {
        setDiffReport(report);
      })
      .catch((err) => {
        setError(err.message || 'Failed to compare plan versions.');
      })
      .finally(() => {
        setDiffLoading(false);
      });
  }, [selectedVA, selectedVB, planId]);

  if (!isOpen) return null;

  return (
    <div
      className={styles.modalBackdrop}
      role="dialog"
      aria-modal="true"
      aria-labelledby="version-diff-title"
      data-testid="plan-version-diff-modal"
    >
      <div className={styles.modalContent}>
        <header className={styles.modalHeader}>
          <h2 id="version-diff-title" className={styles.modalTitle}>
            Plan Snapshots & Diff Analysis
          </h2>
          <button
            type="button"
            className={styles.closeBtn}
            onClick={onClose}
            aria-label="Close dialog"
            data-testid="close-diff-modal-btn"
          >
            ✕
          </button>
        </header>

        <div className={styles.modalBody}>
          {loading ? (
            <p style={{ textAlign: 'center', padding: 'var(--space-6)' }}>
              Loading snapshot history...
            </p>
          ) : error ? (
            <div style={{ color: 'var(--color-status-danger-text)' }}>{error}</div>
          ) : versions.length === 0 ? (
            <div className={styles.emptyChanges}>
              No submitted snapshots exist for this plan yet. Submit your plan to create an
              immutable version snapshot.
            </div>
          ) : (
            <>
              {/* Snapshot Comparison Selectors */}
              <div className={styles.versionSelectRow}>
                <div className={styles.versionSelectGroup}>
                  <label htmlFor="select-version-a">Base Version:</label>
                  <select
                    id="select-version-a"
                    className={styles.selectInput}
                    value={selectedVA ?? ''}
                    onChange={(e) => setSelectedVA(Number(e.target.value))}
                    data-testid="select-version-a"
                  >
                    {versions.map((v) => (
                      <option key={v.id} value={v.version_number}>
                        Version {v.version_number} (
                        {new Date(v.submitted_at).toLocaleDateString()})
                      </option>
                    ))}
                  </select>
                </div>

                <div className={styles.versionSelectGroup}>
                  <label htmlFor="select-version-b">Target Version:</label>
                  <select
                    id="select-version-b"
                    className={styles.selectInput}
                    value={selectedVB ?? ''}
                    onChange={(e) => setSelectedVB(Number(e.target.value))}
                    data-testid="select-version-b"
                  >
                    {versions.map((v) => (
                      <option key={v.id} value={v.version_number}>
                        Version {v.version_number} (
                        {new Date(v.submitted_at).toLocaleDateString()})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {diffLoading ? (
                <p style={{ textAlign: 'center', padding: 'var(--space-4)' }}>
                  Calculating version diffs...
                </p>
              ) : diffReport ? (
                <>
                  <div className={styles.diffSummaryGrid}>
                    <div className={`${styles.summaryCard} ${styles.summaryAdded}`}>
                      <span className={styles.summaryCount}>
                        +{diffReport.items_added.length}
                      </span>
                      <span className={styles.summaryLabel}>Courses Added</span>
                    </div>

                    <div className={`${styles.summaryCard} ${styles.summaryRemoved}`}>
                      <span className={styles.summaryCount}>
                        -{diffReport.items_removed.length}
                      </span>
                      <span className={styles.summaryLabel}>Courses Removed</span>
                    </div>

                    <div className={`${styles.summaryCard} ${styles.summaryMoved}`}>
                      <span className={styles.summaryCount}>
                        {diffReport.items_moved.length}
                      </span>
                      <span className={styles.summaryLabel}>Terms Shifted</span>
                    </div>
                  </div>

                  {/* Detailed Diff Sections */}
                  {diffReport.items_added.length > 0 && (
                    <div className={styles.diffSection}>
                      <h3 className={styles.sectionHeader}>Courses Added</h3>
                      <ul className={styles.changeList}>
                        {diffReport.items_added.map((item, idx) => (
                          <li
                            key={idx}
                            className={`${styles.changeItem} ${styles.itemAdded}`}
                            data-testid="diff-item-added"
                          >
                            <span>
                              <strong>{item.course_code}</strong> - {item.course_title}
                            </span>
                            <span>Term {item.term_index} ({item.term_code})</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {diffReport.items_removed.length > 0 && (
                    <div className={styles.diffSection}>
                      <h3 className={styles.sectionHeader}>Courses Removed</h3>
                      <ul className={styles.changeList}>
                        {diffReport.items_removed.map((item, idx) => (
                          <li
                            key={idx}
                            className={`${styles.changeItem} ${styles.itemRemoved}`}
                            data-testid="diff-item-removed"
                          >
                            <span>
                              <strong>{item.course_code}</strong> - {item.course_title}
                            </span>
                            <span>Term {item.term_index} ({item.term_code})</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {diffReport.items_moved.length > 0 && (
                    <div className={styles.diffSection}>
                      <h3 className={styles.sectionHeader}>Courses Rescheduled</h3>
                      <ul className={styles.changeList}>
                        {diffReport.items_moved.map((item, idx) => (
                          <li
                            key={idx}
                            className={`${styles.changeItem} ${styles.itemMoved}`}
                            data-testid="diff-item-moved"
                          >
                            <span>
                              <strong>{item.course_code}</strong> - {item.course_title}
                            </span>
                            <span>
                              {item.from_term} (T{item.from_index}) → {item.to_term} (T
                              {item.to_index})
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {diffReport.items_added.length === 0 &&
                    diffReport.items_removed.length === 0 &&
                    diffReport.items_moved.length === 0 && (
                      <div className={styles.emptyChanges}>
                        No course differences found between Version {selectedVA} and Version{' '}
                        {selectedVB}.
                      </div>
                    )}
                </>
              ) : null}

              {/* Version List History */}
              <div className={styles.diffSection}>
                <h3 className={styles.sectionHeader}>Snapshot Submission Audit Log</h3>
                <table className={styles.historyTable} data-testid="snapshots-history-table">
                  <thead>
                    <tr>
                      <th>Version</th>
                      <th>Status</th>
                      <th>Submitted By</th>
                      <th>Date</th>
                      <th>Submission Note</th>
                    </tr>
                  </thead>
                  <tbody>
                    {versions.map((v) => (
                      <tr key={v.id}>
                        <td>v{v.version_number}</td>
                        <td>{v.status}</td>
                        <td>{v.submitted_by_username || 'Advisor / Student'}</td>
                        <td>{new Date(v.submitted_at).toLocaleString()}</td>
                        <td>{v.submission_note || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
