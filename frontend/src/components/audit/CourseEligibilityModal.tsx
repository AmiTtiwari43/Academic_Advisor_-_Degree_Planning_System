import React, { useEffect, useState } from 'react';
import { CourseEligibilityResult, academicRecordsApi } from '../../api/academicRecords';
import styles from './CourseEligibilityModal.module.css';

interface CourseEligibilityModalProps {
  isOpen: boolean;
  onClose: () => void;
  recordId: string;
  courseId: string;
  courseCode: string;
  courseTitle: string;
}

export const CourseEligibilityModal: React.FC<CourseEligibilityModalProps> = ({
  isOpen,
  onClose,
  recordId,
  courseId,
  courseCode,
  courseTitle,
}) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CourseEligibilityResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !courseId || !recordId) return;

    let isMounted = true;
    setLoading(true);
    setError(null);
    setResult(null);

    academicRecordsApi
      .checkCourseEligibility(recordId, courseId)
      .then((data) => {
        if (isMounted) {
          setResult(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || 'Failed to evaluate prerequisite eligibility.');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, courseId, recordId]);

  if (!isOpen) return null;

  return (
    <div className={styles.modalOverlay} role="dialog" aria-modal="true" aria-labelledby="eligibility-title">
      <div className={styles.modalContent} data-testid="course-eligibility-modal">
        <header className={styles.modalHeader}>
          <div>
            <span className={styles.headerSubtitle}>Prerequisite Eligibility Audit</span>
            <h2 id="eligibility-title" className={styles.courseHeader}>
              <span className={styles.courseCode}>{courseCode}</span> — {courseTitle}
            </h2>
          </div>
          <button
            type="button"
            className={styles.closeBtn}
            onClick={onClose}
            aria-label="Close dialog"
            data-testid="close-eligibility-modal"
          >
            ✕
          </button>
        </header>

        <div className={styles.modalBody}>
          {loading && (
            <div className={styles.loadingContainer} data-testid="eligibility-loading">
              <div className={styles.spinner} />
              <p>Evaluating prerequisites against pinned curriculum rules engine...</p>
            </div>
          )}

          {error && (
            <div className={styles.errorBanner} data-testid="eligibility-error">
              <strong>Error Evaluating Course:</strong> {error}
            </div>
          )}

          {result && !loading && (
            <div className={styles.resultContainer} data-testid="eligibility-result">
              {/* Verdict Banner */}
              <div
                className={`${styles.verdictBanner} ${
                  result.eligible ? styles.verdictSatisfied : styles.verdictUnsatisfied
                }`}
                data-testid="eligibility-verdict"
              >
                <div className={styles.verdictIcon}>
                  {result.eligible ? '✓' : '✗'}
                </div>
                <div>
                  <h3 className={styles.verdictTitle}>
                    {result.eligible ? 'Prerequisites Satisfied' : 'Prerequisites Not Met'}
                  </h3>
                  <p className={styles.verdictMessage}>
                    {result.eligible
                      ? 'Student satisfies all prerequisite rules for this course.'
                      : 'Student does not currently meet one or more prerequisite conditions.'}
                  </p>
                </div>
              </div>

              {/* Blocking Reasons */}
              {!result.eligible && result.blocking_reasons.length > 0 && (
                <div className={styles.blockingSection} data-testid="eligibility-blocking-reasons">
                  <h4 className={styles.sectionHeading}>Outstanding Deficiencies:</h4>
                  <ul className={styles.blockingList}>
                    {result.blocking_reasons.map((reason, idx) => (
                      <li key={idx} className={styles.blockingItem}>
                        {reason}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Pure Python Execution Tree Breakdown */}
              {result.execution_tree && (
                <div className={styles.treeSection}>
                  <h4 className={styles.sectionHeading}>Rule Evaluation Trace (Engine Parity):</h4>
                  <pre className={styles.treeOutput}>
                    {JSON.stringify(result.execution_tree, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>

        <footer className={styles.modalFooter}>
          <button
            type="button"
            className={styles.primaryBtn}
            onClick={onClose}
          >
            Close
          </button>
        </footer>
      </div>
    </div>
  );
};
