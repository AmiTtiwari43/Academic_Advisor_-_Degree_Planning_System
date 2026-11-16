import React from 'react';
import { Exemption, TranscriptEntry, TransferCredit } from '../../api/academicRecords';
import styles from './TranscriptTable.module.css';

interface TranscriptTableProps {
  entries: TranscriptEntry[];
  transfers: TransferCredit[];
  exemptions: Exemption[];
}

export const TranscriptTable: React.FC<TranscriptTableProps> = ({
  entries,
  transfers,
  exemptions,
}) => {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return styles.statusCompleted;
      case 'IN_PROGRESS':
        return styles.statusInProgress;
      case 'FAILED':
        return styles.statusFailed;
      default:
        return styles.statusOther;
    }
  };

  const getVerificationBadge = (vStatus: string) => {
    switch (vStatus) {
      case 'VERIFIED':
        return styles.vBadgeVerified;
      case 'PENDING':
        return styles.vBadgePending;
      default:
        return styles.vBadgeUnverified;
    }
  };

  return (
    <div className={styles.container} data-testid="transcript-table-view">
      {/* Institutional Transcript Entries */}
      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <h3 className={styles.sectionTitle}>Institutional Transcript Entries</h3>
          <span className={styles.countBadge}>{entries.length} Entries</span>
        </div>

        {entries.length === 0 ? (
          <div className={styles.emptyState}>No transcript records found for this student.</div>
        ) : (
          <div className={styles.tableResponsive}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Term</th>
                  <th>Course Code</th>
                  <th>Course Title</th>
                  <th>Grade</th>
                  <th>Attempted</th>
                  <th>Earned</th>
                  <th>Attempt</th>
                  <th>Status</th>
                  <th>Verification</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <tr key={entry.id}>
                    <td className={styles.termCell}>{entry.term_code}</td>
                    <td className={styles.codeCell}>{entry.course_code}</td>
                    <td>{entry.course_title}</td>
                    <td className={styles.gradeCell}>
                      <strong>{entry.grade || '—'}</strong>
                      {entry.grade_points !== undefined && entry.grade_points !== null && (
                        <span style={{ fontSize: '0.72rem', color: '#64748B', display: 'block' }}>
                          {Number(entry.grade_points).toFixed(1)} / 10.0
                        </span>
                      )}
                    </td>
                    <td>{entry.credits_attempted}</td>
                    <td>
                      <strong className={Number(entry.credits_earned) > 0 ? styles.earnedCredits : ''}>
                        {entry.credits_earned}
                      </strong>
                    </td>
                    <td>#{entry.attempt_number}</td>
                    <td>
                      <span className={`${styles.badge} ${getStatusBadge(entry.status)}`}>
                        {entry.status}
                      </span>
                    </td>
                    <td>
                      <span className={`${styles.badge} ${getVerificationBadge(entry.verification_status)}`}>
                        {entry.verification_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Transfer Credits Section */}
      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <h3 className={styles.sectionTitle}>External Transfer Credits</h3>
          <span className={styles.countBadge}>{transfers.length} Transferred</span>
        </div>

        {transfers.length === 0 ? (
          <div className={styles.emptyState}>No transfer credits registered.</div>
        ) : (
          <div className={styles.tableResponsive}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Course Code</th>
                  <th>Title</th>
                  <th>Source Institution</th>
                  <th>Credits</th>
                  <th>Grade</th>
                  <th>Verification</th>
                </tr>
              </thead>
              <tbody>
                {transfers.map((tc) => (
                  <tr key={tc.id}>
                    <td className={styles.codeCell}>{tc.course_code}</td>
                    <td>{tc.course_title}</td>
                    <td>{tc.source_institution}</td>
                    <td>{tc.credits}</td>
                    <td>{tc.grade}</td>
                    <td>
                      <span className={`${styles.badge} ${tc.is_verified ? styles.vBadgeVerified : styles.vBadgeUnverified}`}>
                        {tc.is_verified ? 'VERIFIED' : 'UNVERIFIED'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Course Exemptions Section */}
      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <h3 className={styles.sectionTitle}>Approved Course Exemptions</h3>
          <span className={styles.countBadge}>{exemptions.length} Exemptions</span>
        </div>

        {exemptions.length === 0 ? (
          <div className={styles.emptyState}>No course exemptions recorded.</div>
        ) : (
          <div className={styles.tableResponsive}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Course Code</th>
                  <th>Title</th>
                  <th>Reason / Justification</th>
                  <th>Approved By</th>
                  <th>Approved Date</th>
                </tr>
              </thead>
              <tbody>
                {exemptions.map((ex) => (
                  <tr key={ex.id}>
                    <td className={styles.codeCell}>{ex.course_code}</td>
                    <td>{ex.course_title}</td>
                    <td>{ex.reason}</td>
                    <td>{ex.approved_by_username || 'Academic Advisor'}</td>
                    <td>{new Date(ex.approved_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
};
