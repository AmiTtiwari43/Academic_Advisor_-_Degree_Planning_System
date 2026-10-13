import React, { useEffect, useState } from 'react';
import {
  DegreeAuditReport,
  StudentRecord,
  StudentRecordDetail,
  academicRecordsApi,
} from '../api/academicRecords';
import { DegreeAuditProgressBar } from '../components/audit/DegreeAuditProgressBar';
import { RequirementGroupAccordion } from '../components/audit/RequirementGroupAccordion';
import { CourseEligibilityModal } from '../components/audit/CourseEligibilityModal';
import { TranscriptTable } from '../components/audit/TranscriptTable';
import styles from './DegreeAuditPage.module.css';

export const DegreeAuditPage: React.FC = () => {
  const [studentRecords, setStudentRecords] = useState<StudentRecord[]>([]);
  const [selectedRecordId, setSelectedRecordId] = useState<string>('');
  const [recordDetail, setRecordDetail] = useState<StudentRecordDetail | null>(null);
  const [auditReport, setAuditReport] = useState<DegreeAuditReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'audit' | 'transcript'>('audit');

  // Eligibility Modal State
  const [eligibilityModalOpen, setEligibilityModalOpen] = useState(false);
  const [selectedCourseForEligibility, setSelectedCourseForEligibility] = useState<{
    id: string;
    code: string;
    title: string;
  } | null>(null);

  // Fetch initial student records
  useEffect(() => {
    let isMounted = true;
    academicRecordsApi
      .getStudentRecords()
      .then((records) => {
        if (!isMounted) return;
        setStudentRecords(records);
        if (records.length > 0) {
          setSelectedRecordId(records[0].id);
        } else {
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err.message || 'Failed to load student records.');
        setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Fetch record detail and audit report when selectedRecordId changes
  const loadAuditData = (recordId: string, isRefresh = false) => {
    if (!recordId) return;
    if (isRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError(null);

    Promise.all([
      academicRecordsApi.getStudentRecord(recordId),
      academicRecordsApi.getStudentRecordAudit(recordId),
    ])
      .then(([detail, audit]) => {
        setRecordDetail(detail);
        setAuditReport(audit);
      })
      .catch((err) => {
        setError(err.message || 'Failed to generate degree audit.');
      })
      .finally(() => {
        setLoading(false);
        setRefreshing(false);
      });
  };

  useEffect(() => {
    if (selectedRecordId) {
      loadAuditData(selectedRecordId);
    }
  }, [selectedRecordId]);

  const handleCheckEligibility = (courseId: string, courseCode: string, courseTitle: string) => {
    setSelectedCourseForEligibility({ id: courseId, code: courseCode, title: courseTitle });
    setEligibilityModalOpen(true);
  };

  return (
    <div className={styles.pageContainer} data-testid="degree-audit-page">
      {/* Header */}
      <header className={styles.pageHeader}>
        <div>
          <span className={styles.preTitle}>Authoritative Degree Clearance</span>
          <h1 className={styles.pageTitle}>Degree Audit & Academic Progress</h1>
          <p className={styles.pageDescription}>
            Deterministic audit evaluation computed strictly against the student&apos;s pinned curriculum version.
          </p>
        </div>

        <div className={styles.headerActions}>
          {studentRecords.length > 1 && (
            <div className={styles.selectorWrapper}>
              <label htmlFor="student-selector" className={styles.selectorLabel}>
                Advisee Record:
              </label>
              <select
                id="student-selector"
                value={selectedRecordId}
                onChange={(e) => setSelectedRecordId(e.target.value)}
                className={styles.studentSelect}
                data-testid="student-record-select"
              >
                {studentRecords.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.student_username} ({r.programme_code})
                  </option>
                ))}
              </select>
            </div>
          )}

          <button
            type="button"
            className={styles.refreshButton}
            onClick={() => loadAuditData(selectedRecordId, true)}
            disabled={refreshing || loading}
            data-testid="refresh-audit-button"
          >
            {refreshing ? 'Evaluating...' : '↻ Recalculate Audit'}
          </button>
        </div>
      </header>

      {/* Student Meta Banner */}
      {recordDetail && (
        <section className={styles.metaBanner} data-testid="student-meta-banner">
          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>Student</span>
            <span className={styles.metaValue}>
              {recordDetail.student_first_name
                ? `${recordDetail.student_first_name} ${recordDetail.student_last_name}`
                : recordDetail.student_username}
            </span>
            <span className={styles.metaSub}>{recordDetail.student_email}</span>
          </div>

          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>Programme & Catalog</span>
            <span className={styles.metaValue}>
              {recordDetail.programme_name} ({recordDetail.programme_code})
            </span>
            <span className={styles.metaSub}>
              Pinned Curriculum: v{recordDetail.curriculum_version_number}
            </span>
          </div>

          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>Enrollment & Policy</span>
            <span className={styles.metaValue}>Enrolled: {recordDetail.enrollment_term_code}</span>
            <span className={styles.metaSub}>
              Repeats: {recordDetail.repeated_course_policy}
            </span>
          </div>

          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>Academic Status</span>
            <span className={styles.statusBadgeActive}>{recordDetail.status}</span>
          </div>
        </section>
      )}

      {/* Tabs */}
      <div className={styles.tabNav}>
        <button
          type="button"
          className={`${styles.tabBtn} ${activeTab === 'audit' ? styles.tabBtnActive : ''}`}
          onClick={() => setActiveTab('audit')}
          data-testid="tab-degree-audit"
        >
          Degree Audit Analysis
        </button>
        <button
          type="button"
          className={`${styles.tabBtn} ${activeTab === 'transcript' ? styles.tabBtnActive : ''}`}
          onClick={() => setActiveTab('transcript')}
          data-testid="tab-transcript-history"
        >
          Official History & Transcript ({recordDetail?.transcript_entries.length ?? 0})
        </button>
      </div>

      {/* Main Content States */}
      {loading && !refreshing && (
        <div className={styles.loadingBox} data-testid="audit-loading-state">
          <div className={styles.spinner} />
          <p>Running comprehensive degree audit against curriculum rule engine...</p>
        </div>
      )}

      {error && (
        <div className={styles.errorBox} data-testid="audit-error-state">
          <h3>Audit Evaluation Error</h3>
          <p>{error}</p>
          <button
            type="button"
            className={styles.retryButton}
            onClick={() => loadAuditData(selectedRecordId)}
          >
            Try Again
          </button>
        </div>
      )}

      {!loading && !error && !auditReport && (
        <div className={styles.emptyBox}>
          <h3>No Academic Records</h3>
          <p>No active student record or curriculum version assigned to evaluate.</p>
        </div>
      )}

      {!loading && !error && auditReport && (
        <>
          {activeTab === 'audit' && (
            <div className={styles.auditContent}>
              {/* Overall Progress Metric Card */}
              <DegreeAuditProgressBar
                totalRequired={auditReport.total_credits_required}
                totalEarned={auditReport.total_credits_earned}
                totalInProgress={auditReport.total_credits_in_progress}
                remainingRequired={auditReport.remaining_credits_required}
                cgpa={auditReport.overall_cgpa}
                minCgpa={auditReport.min_cgpa_required}
                isDegreeSatisfied={auditReport.is_degree_satisfied}
              />

              {/* Requirement Groups Breakdown */}
              <div className={styles.groupsSection}>
                <div className={styles.groupsHeader}>
                  <h2 className={styles.sectionTitle}>Curriculum Requirement Groups</h2>
                  <span className={styles.groupsCount}>
                    {auditReport.groups.filter((g) => g.is_satisfied).length} of{' '}
                    {auditReport.groups.length} Groups Satisfied
                  </span>
                </div>

                <div className={styles.groupsList}>
                  {auditReport.groups.map((grp) => (
                    <RequirementGroupAccordion
                      key={grp.group_id}
                      group={grp}
                      onCheckEligibility={handleCheckEligibility}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'transcript' && recordDetail && (
            <div className={styles.transcriptContent}>
              <TranscriptTable
                entries={recordDetail.transcript_entries}
                transfers={recordDetail.transfer_credits}
                exemptions={recordDetail.exemptions}
              />
            </div>
          )}
        </>
      )}

      {/* Prerequisite Eligibility Check Modal */}
      {selectedCourseForEligibility && (
        <CourseEligibilityModal
          isOpen={eligibilityModalOpen}
          onClose={() => {
            setEligibilityModalOpen(false);
            setSelectedCourseForEligibility(null);
          }}
          recordId={selectedRecordId}
          courseId={selectedCourseForEligibility.id}
          courseCode={selectedCourseForEligibility.code}
          courseTitle={selectedCourseForEligibility.title}
        />
      )}
    </div>
  );
};
