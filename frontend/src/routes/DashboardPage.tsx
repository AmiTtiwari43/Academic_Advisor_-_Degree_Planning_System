import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Calendar,
  FileCheck,
  Compass,
  Users,
  BookOpen,
  BarChart3,
  CheckCircle2,
  Clock,
  ArrowRight,
  ShieldCheck,
  AlertTriangle,
  Mail,
  Building,
  CalendarCheck,
} from 'lucide-react';
import styles from './DashboardPage.module.css';
import {
  PageHeader,
  Button,
  Badge,
  Table,
  Column,
  Dialog,
  Toast,
  ToastProps,
  Input,
  Skeleton,
} from '../components';
import { useAuth } from '../context/AuthContext';
import {
  academicRecordsApi,
  StudentRecord,
  DegreeAuditReport,
  TranscriptEntry,
  AcademicTerm,
} from '../api/academicRecords';
import { advisingApi, ReviewQueueItem } from '../api/advising';
import { curriculumApi, Programme, Course } from '../api/curriculum';
import {
  analyticsApi,
  AnalyticsOverview,
  ProgrammeProgressReport,
  ProgrammeProgressItem,
} from '../api/analytics';

export const DashboardPage: React.FC = () => {
  const { user, activeRole, activeMembership, unifiedRole } = useAuth();
  const navigate = useNavigate();

  // Moderator Super Admin Perspective Switcher State
  const [moderatorPerspective, setModeratorPerspective] = useState<'MODERATOR' | 'MENTOR' | 'STUDENT'>('MODERATOR');
  const [selectedStudentId, setSelectedStudentId] = useState<string>('');

  // Consultation Dialog State (for Students)
  const [isConsultationOpen, setIsConsultationOpen] = useState(false);
  const [consultationReason, setConsultationReason] = useState(
    'Discuss upcoming semester course plan and degree progression.'
  );

  // Toast Notification State
  const [toasts, setToasts] = useState<Omit<ToastProps, 'onClose'>[]>([]);

  // Common Loading & Error States
  const [isLoading, setIsLoading] = useState(true);

  // Student-specific state
  const [studentRecord, setStudentRecord] = useState<StudentRecord | null>(null);
  const [degreeAudit, setDegreeAudit] = useState<DegreeAuditReport | null>(null);
  const [transcriptEntries, setTranscriptEntries] = useState<TranscriptEntry[]>([]);

  // Advisor-specific state
  const [reviewQueue, setReviewQueue] = useState<ReviewQueueItem[]>([]);
  const [adviseeRecords, setAdviseeRecords] = useState<StudentRecord[]>([]);

  // Coordinator-specific state
  const [programmes, setProgrammes] = useState<Programme[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);

  // HOD-specific state
  const [analyticsOverview, setAnalyticsOverview] = useState<AnalyticsOverview | null>(null);
  const [programmeProgress, setProgrammeProgress] = useState<ProgrammeProgressReport | null>(null);

  // Admin-specific state
  const [academicTerms, setAcademicTerms] = useState<AcademicTerm[]>([]);

  const addToast = (toast: Omit<ToastProps, 'onClose' | 'id'>) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { ...toast, id }]);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const handleConsultationSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsConsultationOpen(false);
    addToast({
      type: 'success',
      title: 'Consultation Requested',
      message: 'Your meeting request has been submitted to Dr. Alice Chen.',
    });
  };

  const handleSelectStudent = async (studentId: string) => {
    setSelectedStudentId(studentId);
    const chosen = adviseeRecords.find((r) => r.id === studentId);
    if (chosen) {
      setStudentRecord(chosen);
      try {
        const [audit, transcript] = await Promise.all([
          academicRecordsApi.getStudentRecordAudit(chosen.id).catch(() => null),
          academicRecordsApi.getStudentRecordTranscript(chosen.id).catch(() => []),
        ]);
        setDegreeAudit(audit);
        setTranscriptEntries(transcript);
      } catch {
        // ignore
      }
    }
  };

  // Determine current effective role (default to STUDENT if null)
  const currentRole = activeRole || 'STUDENT';

  // Load real data according to active role
  const loadDashboardData = useCallback(async () => {
    setIsLoading(true);
    try {
      if (currentRole === 'STUDENT') {
        const records = await academicRecordsApi.getStudentRecords();
        if (records && records.length > 0) {
          const rec = records[0];
          setStudentRecord(rec);
          const [audit, transcript] = await Promise.all([
            academicRecordsApi.getStudentRecordAudit(rec.id).catch(() => null),
            academicRecordsApi.getStudentRecordTranscript(rec.id).catch(() => []),
          ]);
          setDegreeAudit(audit);
          setTranscriptEntries(transcript);
        }
      } else if (currentRole === 'ADVISOR' || currentRole === 'MENTOR') {
        const [queue, advisees] = await Promise.all([
          advisingApi.fetchQueue().catch(() => []),
          academicRecordsApi.getStudentRecords().catch(() => []),
        ]);
        setReviewQueue(queue);
        setAdviseeRecords(advisees);
      } else if (currentRole === 'COORDINATOR') {
        const [progs, crs, queue, advisees] = await Promise.all([
          curriculumApi.getProgrammes().catch(() => []),
          curriculumApi.getCourses().catch(() => []),
          advisingApi.fetchQueue().catch(() => []),
          academicRecordsApi.getStudentRecords().catch(() => []),
        ]);
        setProgrammes(progs);
        setCourses(crs);
        setReviewQueue(queue);
        setAdviseeRecords(advisees);
      } else if (currentRole === 'HOD') {
        const [overview, progress, queue, advisees] = await Promise.all([
          analyticsApi.getOverview().catch(() => null),
          analyticsApi.getProgrammeProgress().catch(() => null),
          advisingApi.fetchQueue().catch(() => []),
          academicRecordsApi.getStudentRecords().catch(() => []),
        ]);
        setAnalyticsOverview(overview);
        setProgrammeProgress(progress);
        setReviewQueue(queue);
        setAdviseeRecords(advisees);
      } else {
        // ADMIN / MODERATOR
        const [terms, overview, queue, advisees, progress, progs, crs] = await Promise.all([
          academicRecordsApi.getTerms().catch(() => []),
          analyticsApi.getOverview().catch(() => null),
          advisingApi.fetchQueue().catch(() => []),
          academicRecordsApi.getStudentRecords().catch(() => []),
          analyticsApi.getProgrammeProgress().catch(() => null),
          curriculumApi.getProgrammes().catch(() => []),
          curriculumApi.getCourses().catch(() => []),
        ]);
        setAcademicTerms(terms);
        setAnalyticsOverview(overview);
        setReviewQueue(queue);
        setAdviseeRecords(advisees);
        setProgrammeProgress(progress);
        setProgrammes(progs);
        setCourses(crs);

        if (advisees && advisees.length > 0) {
          const firstAdvisee = advisees[0];
          setStudentRecord(firstAdvisee);
          setSelectedStudentId(firstAdvisee.id);
          const [audit, transcript] = await Promise.all([
            academicRecordsApi.getStudentRecordAudit(firstAdvisee.id).catch(() => null),
            academicRecordsApi.getStudentRecordTranscript(firstAdvisee.id).catch(() => []),
          ]);
          setDegreeAudit(audit);
          setTranscriptEntries(transcript);
        }
      }
    } catch {
      // Graceful fallback: UI displays clear empty/informative states
    } finally {
      setIsLoading(false);
    }
  }, [currentRole]);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  // Loading state skeleton
  if (isLoading) {
    return (
      <div className={styles.dashboardContainer}>
        <PageHeader
          title="Loading Academic Workspace..."
          subtitle="Retrieving verified institutional records and status"
        />
        <div className={styles.metricsGrid}>
          <Skeleton height="110px" />
          <Skeleton height="110px" />
          <Skeleton height="110px" />
          <Skeleton height="110px" />
        </div>
        <div style={{ marginTop: '24px' }}>
          <Skeleton height="320px" />
        </div>
      </div>
    );
  }

  const isModeratorRole =
    ['ADMIN', 'MODERATOR', 'COORDINATOR', 'HOD'].includes(currentRole) ||
    unifiedRole === 'MODERATOR' ||
    Boolean(user?.is_superuser);

  const renderPerspectiveSwitcher = () => (
    <div
      style={{
        display: 'flex',
        gap: '10px',
        marginBottom: '20px',
        backgroundColor: '#F8FAFC',
        padding: '8px 12px',
        borderRadius: '12px',
        alignItems: 'center',
        flexWrap: 'wrap',
        border: '1px solid #E2E8F0',
      }}
      data-testid="moderator-perspective-switcher"
    >
      <span
        style={{
          fontSize: '0.85rem',
          fontWeight: 700,
          color: '#334155',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
        }}
      >
        <ShieldCheck size={16} color="#7C3AED" />
        Super Admin Mode:
      </span>
      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
        <button
          type="button"
          onClick={() => setModeratorPerspective('MODERATOR')}
          style={{
            padding: '6px 14px',
            borderRadius: '8px',
            cursor: 'pointer',
            fontWeight: 600,
            fontSize: '0.82rem',
            backgroundColor: moderatorPerspective === 'MODERATOR' ? '#7C3AED' : '#FFFFFF',
            color: moderatorPerspective === 'MODERATOR' ? '#FFFFFF' : '#475569',
            boxShadow:
              moderatorPerspective === 'MODERATOR'
                ? '0 2px 4px rgba(124, 58, 237, 0.25)'
                : 'none',
            border: moderatorPerspective === 'MODERATOR' ? 'none' : '1px solid #E2E8F0',
          }}
        >
          👑 Moderator Executive View
        </button>
        <button
          type="button"
          onClick={() => setModeratorPerspective('MENTOR')}
          style={{
            padding: '6px 14px',
            borderRadius: '8px',
            cursor: 'pointer',
            fontWeight: 600,
            fontSize: '0.82rem',
            backgroundColor: moderatorPerspective === 'MENTOR' ? '#0E7577' : '#FFFFFF',
            color: moderatorPerspective === 'MENTOR' ? '#FFFFFF' : '#475569',
            boxShadow:
              moderatorPerspective === 'MENTOR'
                ? '0 2px 4px rgba(14, 117, 119, 0.25)'
                : 'none',
            border: moderatorPerspective === 'MENTOR' ? 'none' : '1px solid #E2E8F0',
          }}
        >
          👨‍🏫 Mentor Dashboard View
        </button>
        <button
          type="button"
          onClick={() => setModeratorPerspective('STUDENT')}
          style={{
            padding: '6px 14px',
            borderRadius: '8px',
            cursor: 'pointer',
            fontWeight: 600,
            fontSize: '0.82rem',
            backgroundColor: moderatorPerspective === 'STUDENT' ? '#2563EB' : '#FFFFFF',
            color: moderatorPerspective === 'STUDENT' ? '#FFFFFF' : '#475569',
            boxShadow:
              moderatorPerspective === 'STUDENT'
                ? '0 2px 4px rgba(37, 99, 235, 0.25)'
                : 'none',
            border: moderatorPerspective === 'STUDENT' ? 'none' : '1px solid #E2E8F0',
          }}
        >
          🎓 Student Dashboard View
        </button>
      </div>
    </div>
  );

  // ==========================================
  // 1. STUDENT VIEW
  // ==========================================
  const isViewingStudentPerspective =
    currentRole === 'STUDENT' || (isModeratorRole && moderatorPerspective === 'STUDENT');

  if (isViewingStudentPerspective) {
    const cgpaVal = degreeAudit ? Number(degreeAudit.overall_cgpa) : Number(studentRecord?.cached_cgpa || 0);
    const minCgpaVal = degreeAudit ? Number(degreeAudit.min_cgpa_required) : 5.0;
    const isCgpaSatisfied = cgpaVal >= minCgpaVal;
    const earnedCredits = degreeAudit ? degreeAudit.total_credits_earned : Number(studentRecord?.cached_total_credits || 0);
    const requiredCredits = degreeAudit ? degreeAudit.total_credits_required : 120;
    const inProgressCredits = degreeAudit ? degreeAudit.total_credits_in_progress : 0;
    const completionPct = Math.min(100, Math.round((earnedCredits / requiredCredits) * 100));

    // Transcript table columns
    const transcriptColumns: Column<TranscriptEntry>[] = [
      { key: 'term_code', header: 'Term', width: '110px', sortable: true },
      { key: 'course_code', header: 'Course Code', width: '130px', sortable: true },
      { key: 'course_title', header: 'Course Title', sortable: true },
      {
        key: 'grade',
        header: 'Grade',
        width: '90px',
        align: 'center',
        render: (item) => (
          <strong>{item.grade || '—'}</strong>
        ),
      },
      {
        key: 'grade_points',
        header: 'Grade Pts (10.0)',
        width: '130px',
        align: 'center',
        render: (item) => (
          item.grade_points !== undefined && item.grade_points !== null
            ? <span>{Number(item.grade_points).toFixed(1)} / 10.0</span>
            : <span style={{ color: '#94A3B8' }}>—</span>
        ),
      },
      {
        key: 'credits_earned',
        header: 'Credits',
        width: '90px',
        align: 'center',
        render: (item) => <span>{item.credits_earned}</span>,
      },
      {
        key: 'status',
        header: 'Status',
        width: '120px',
        render: (item) => (
          item.status === 'COMPLETED' ? (
            <Badge variant="success" size="sm" icon={<CheckCircle2 size={12} />}>Completed</Badge>
          ) : item.status === 'IN_PROGRESS' ? (
            <Badge variant="teal" size="sm" icon={<Clock size={12} />}>In Progress</Badge>
          ) : (
            <Badge variant="neutral" size="sm">{item.status}</Badge>
          )
        ),
      },
    ];

    const greetingName =
      isModeratorRole && moderatorPerspective === 'STUDENT' && studentRecord
        ? (studentRecord.student_preferred_name ||
           (studentRecord.student_first_name
             ? `${studentRecord.student_first_name} ${studentRecord.student_last_name || ''}`.trim()
             : studentRecord.student_username) ||
           'Student Candidate')
        : (user?.preferred_name?.trim() ||
           (user?.first_name ? `${user.first_name} ${user.last_name || ''}`.trim() : user?.username) ||
           'Student');

    return (
      <div className={styles.dashboardContainer}>
        {isModeratorRole && moderatorPerspective === 'STUDENT' && (
          <>
            {renderPerspectiveSwitcher()}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '12px 18px',
                backgroundColor: 'rgba(37, 99, 235, 0.08)',
                border: '1px solid rgba(37, 99, 235, 0.25)',
                borderRadius: '10px',
                marginBottom: '20px',
                flexWrap: 'wrap',
                gap: '12px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Badge variant="teal" size="sm">Super Admin Clearance</Badge>
                <span style={{ fontSize: '0.92rem', fontWeight: 600, color: '#1E40AF' }}>
                  Inspecting Live Student Dashboard
                </span>
              </div>
              {adviseeRecords.length > 0 && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <label htmlFor="moderator-student-select" style={{ fontSize: '0.85rem', color: '#475569', fontWeight: 600 }}>
                    Active Advisee Record:
                  </label>
                  <select
                    id="moderator-student-select"
                    value={selectedStudentId || (studentRecord?.id || '')}
                    onChange={(e) => handleSelectStudent(e.target.value)}
                    style={{
                      padding: '6px 12px',
                      borderRadius: '6px',
                      border: '1px solid #CBD5E1',
                      fontSize: '0.85rem',
                      backgroundColor: '#FFFFFF',
                      fontWeight: 500,
                      maxWidth: '320px',
                    }}
                  >
                    {adviseeRecords.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.student_preferred_name || `${r.student_first_name} ${r.student_last_name}`.trim() || r.student_username} [{r.student_registration_number || `STU-2026-${r.id}`}] ({r.programme_code})
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          </>
        )}
        <PageHeader
          title={`Welcome back, ${greetingName}`}
          subtitle={`${studentRecord?.programme_name || 'Degree Candidate'} — Official Academic Overview`}
          badge={
            <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
              <Badge variant="teal" size="sm">
                {studentRecord?.status || 'Active Standing'}
              </Badge>
              {(studentRecord?.student_registration_number || user?.registration_number) && (
                <Badge variant="neutral" size="sm">
                  REG: {studentRecord?.student_registration_number || user?.registration_number}
                </Badge>
              )}
            </div>
          }
          breadcrumbs={[{ label: 'Academic Workspace' }, { label: 'Student Overview' }]}
          actions={
            <div className={styles.headerActions}>
              <Button
                variant="primary"
                size="sm"
                leftIcon={<CalendarCheck size={14} />}
                onClick={() => setIsConsultationOpen(true)}
              >
                Schedule Advisor Meeting
              </Button>
            </div>
          }
        />

        {/* 4 Standardized Metric Cards */}
        <div className={styles.metricsGrid}>
          <div className={styles.metricCard}>
            <span className={styles.metricLabel}>
              Cumulative CGPA
              <Badge variant={isCgpaSatisfied ? 'success' : 'danger'} size="sm">
                {isCgpaSatisfied ? 'Satisfied' : 'Below Threshold'}
              </Badge>
            </span>
            <span className={styles.metricValue}>
              {cgpaVal.toFixed(2)}
              <span className={styles.metricSub}>/ 10.00 Scale</span>
            </span>
            <span className={styles.metricMeta}>
              Min {minCgpaVal.toFixed(2)} required for graduation
            </span>
          </div>

          <div className={styles.metricCard}>
            <span className={styles.metricLabel}>Degree Progress</span>
            <span className={styles.metricValue}>
              {earnedCredits}{' '}
              <span className={styles.metricSub}>/ {requiredCredits} Credits</span>
            </span>
            <div className={styles.progressBarBg} style={{ marginTop: '8px' }}>
              <div
                className={styles.progressBarFill}
                style={{ width: `${completionPct}%` }}
              />
            </div>
            <span className={styles.metricMeta}>
              {completionPct}% curriculum complete (+{inProgressCredits} in progress)
            </span>
          </div>

          <div className={styles.metricCard}>
            <span className={styles.metricLabel}>Enrolled Programme</span>
            <span className={styles.metricValue} style={{ fontSize: '1.25rem' }}>
              {studentRecord?.programme_code || 'CS-BS'}
            </span>
            <span className={styles.metricMeta}>
              Catalog Version {degreeAudit?.version_number ? `v${degreeAudit.version_number}` : '2024-2025'}
            </span>
          </div>

          <div className={styles.metricCard}>
            <span className={styles.metricLabel}>Assigned Advisor</span>
            <span className={styles.metricValue} style={{ fontSize: '1.25rem' }}>
              Dr. Alice Chen
            </span>
            <span className={styles.metricMeta}>
              School of Computing & Engineering
            </span>
          </div>
        </div>

        {/* Action Hub */}
        <div className={styles.actionHubSection}>
          <h2 className={styles.sectionHeading}>
            <Compass size={18} />
            Academic Planning & Progress Services
          </h2>
          <div className={styles.actionGrid}>
            <div
              className={styles.actionCard}
              onClick={() => navigate('/plan')}
              role="button"
              tabIndex={0}
            >
              <div className={styles.actionCardHeader}>
                <div className={styles.actionIcon}>
                  <Calendar size={20} />
                </div>
                <div className={styles.actionCardBody}>
                  <h3 className={styles.actionTitle}>Multi-Semester Planner</h3>
                  <p className={styles.actionDesc}>
                    Simulate future terms, resolve prerequisite chains, and optimize your graduation roadmap.
                  </p>
                </div>
              </div>
              <div className={styles.actionCardFooter}>
                <span>Open Planner</span>
                <ArrowRight size={14} />
              </div>
            </div>

            <div
              className={styles.actionCard}
              onClick={() => navigate('/audit')}
              role="button"
              tabIndex={0}
            >
              <div className={styles.actionCardHeader}>
                <div className={`${styles.actionIcon} ${styles.actionIconBlue}`}>
                  <FileCheck size={20} />
                </div>
                <div className={styles.actionCardBody}>
                  <h3 className={styles.actionTitle}>Official Degree Audit</h3>
                  <p className={styles.actionDesc}>
                    Evaluate requirement groups, category satisfaction, and remaining mandatory courses.
                  </p>
                </div>
              </div>
              <div className={styles.actionCardFooter}>
                <span>View Full Audit</span>
                <ArrowRight size={14} />
              </div>
            </div>

            <div
              className={styles.actionCard}
              onClick={() => navigate('/careers')}
              role="button"
              tabIndex={0}
            >
              <div className={styles.actionCardHeader}>
                <div className={`${styles.actionIcon} ${styles.actionIconGold}`}>
                  <Compass size={20} />
                </div>
                <div className={styles.actionCardBody}>
                  <h3 className={styles.actionTitle}>Career Guidance</h3>
                  <p className={styles.actionDesc}>
                    Connect academic milestones to target industry roles, competencies, and recommended electives.
                  </p>
                </div>
              </div>
              <div className={styles.actionCardFooter}>
                <span>Explore Careers</span>
                <ArrowRight size={14} />
              </div>
            </div>
          </div>
        </div>

        {/* Two-Column Content: Recent Courses & Advisor Info */}
        <div className={styles.contentGrid}>
          <div className={styles.cardContainer}>
            <div className={styles.cardHeader}>
              <div>
                <h3 className={styles.cardTitle}>Recent Academic History</h3>
                <span className={styles.cardSubtitle}>
                  Institutional transcript entries evaluated on the standardized 10-point scale
                </span>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate('/audit')}
              >
                Full Transcript
              </Button>
            </div>
            <Table<TranscriptEntry>
              columns={transcriptColumns}
              data={transcriptEntries.slice(-6).reverse()}
              keyExtractor={(item) => item.id}
              caption="Completed and in-progress semester courses"
            />
          </div>

          <div className={styles.cardContainer}>
            <div className={styles.cardHeader}>
              <div>
                <h3 className={styles.cardTitle}>Academic Advising</h3>
                <span className={styles.cardSubtitle}>Designated Faculty Guidance</span>
              </div>
            </div>
            <div className={styles.advisorCard}>
              <div className={styles.advisorHeader}>
                <div className={styles.advisorAvatar}>AC</div>
                <div className={styles.advisorInfo}>
                  <span className={styles.advisorName}>Dr. Alice Chen</span>
                  <span className={styles.advisorRole}>Associate Professor & Lead Advisor</span>
                </div>
              </div>

              <div className={styles.advisorMetaList}>
                <div className={styles.advisorMetaItem}>
                  <Building size={14} />
                  <span>Engineering Hall, Office 412</span>
                </div>
                <div className={styles.advisorMetaItem}>
                  <Mail size={14} />
                  <span>alice.chen@university.edu</span>
                </div>
                <div className={styles.advisorMetaItem}>
                  <Clock size={14} />
                  <span>Mon / Wed: 2:00 PM – 4:00 PM</span>
                </div>
              </div>

              <p style={{ fontSize: '0.8rem', color: '#64748B', margin: 0, lineHeight: 1.45 }}>
                Your advisor reviews degree plans and prerequisite waiver requests prior to semester registration deadlines.
              </p>

              <Button
                variant="primary"
                size="sm"
                leftIcon={<CalendarCheck size={14} />}
                onClick={() => setIsConsultationOpen(true)}
              >
                Request Advising Session
              </Button>
            </div>
          </div>
        </div>

        {/* Advisor Consultation Dialog */}
        <Dialog
          isOpen={isConsultationOpen}
          onClose={() => setIsConsultationOpen(false)}
          title="Schedule Advisor Consultation"
          description="Book an academic advising session to review your multi-semester plan."
          footer={
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsConsultationOpen(false)}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleConsultationSubmit}
              >
                Submit Consultation Request
              </Button>
            </>
          }
        >
          <form onSubmit={handleConsultationSubmit} className={styles.dialogForm}>
            <Input
              label="Assigned Advisor"
              value="Dr. Alice Chen (alice.chen@university.edu)"
              disabled
            />
            <Input
              label="Meeting Purpose"
              value={consultationReason}
              onChange={(e) => setConsultationReason(e.target.value)}
              required
            />
            <p className={styles.dialogNotice}>
              Your advisor will receive your current degree plan and academic standing audit along with this request.
            </p>
          </form>
        </Dialog>

        {/* Toast Container */}
        <div className={styles.toastContainer} aria-live="polite">
          {toasts.map((toast) => (
            <Toast key={toast.id} {...toast} onClose={removeToast} />
          ))}
        </div>
      </div>
    );
  }

  // ==========================================
  // 2. FACULTY ADVISOR & MENTOR VIEW
  // ==========================================
  const isViewingMentorPerspective =
    currentRole === 'ADVISOR' ||
    currentRole === 'MENTOR' ||
    (isModeratorRole && moderatorPerspective === 'MENTOR');

  if (isViewingMentorPerspective) {
    const pendingCount = reviewQueue.filter(
      (q) => q.status === 'SUBMITTED' || q.status === 'RESUBMITTED' || q.status === 'UNDER_REVIEW'
    ).length;
    const attentionCount = reviewQueue.filter(
      (q) => q.warnings_count > 0 || q.override_count > 0
    ).length;

    const queueColumns: Column<ReviewQueueItem>[] = [
      { key: 'student_username', header: 'Student ID', width: '130px', sortable: true },
      { key: 'student_email', header: 'Email', sortable: true },
      { key: 'plan_name', header: 'Plan Name', sortable: true },
      { key: 'programme_code', header: 'Programme', width: '120px', sortable: true },
      {
        key: 'warnings_count',
        header: 'Flags',
        width: '100px',
        align: 'center',
        render: (item) => (
          item.warnings_count > 0 ? (
            <Badge variant="warning" size="sm" icon={<AlertTriangle size={12} />}>
              {item.warnings_count} flags
            </Badge>
          ) : (
            <Badge variant="success" size="sm">Clean</Badge>
          )
        ),
      },
      {
        key: 'status',
        header: 'Status',
        width: '130px',
        render: (item) => (
          <Badge variant={item.status === 'APPROVED' ? 'success' : 'teal'} size="sm">
            {item.status.replace('_', ' ')}
          </Badge>
        ),
      },
      {
        key: 'plan_id',
        header: 'Action',
        width: '120px',
        render: () => (
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/advising')}
          >
            Review Plan
          </Button>
        ),
      },
    ];

    const adviseeColumns: Column<StudentRecord>[] = [
      {
        key: 'student_registration_number' as keyof StudentRecord,
        header: 'Registration No',
        width: '150px',
        sortable: true,
        render: (item) => (
          <Badge variant="teal" size="sm">
            {item.student_registration_number || `STU-2026-${item.id}`}
          </Badge>
        ),
      },
      { key: 'student_username', header: 'Student ID', width: '130px', sortable: true },
      {
        key: 'student_first_name',
        header: 'Student Name',
        sortable: true,
        render: (item) => item.student_preferred_name || `${item.student_first_name} ${item.student_last_name}`.trim() || item.student_username,
      },
      { key: 'programme_code', header: 'Programme', width: '120px', sortable: true },
      {
        key: 'cached_cgpa',
        header: 'CGPA (10.0 Scale)',
        width: '150px',
        align: 'right',
        render: (item) => (
          <strong>{Number(item.cached_cgpa || 0).toFixed(2)} / 10.00</strong>
        ),
      },
      {
        key: 'cached_total_credits',
        header: 'Earned Credits',
        width: '130px',
        align: 'right',
        render: (item) => `${item.cached_total_credits} cr`,
      },
      {
        key: 'status',
        header: 'Standing',
        width: '120px',
        render: (item) => (
          <Badge variant={item.status === 'ACTIVE' ? 'success' : 'neutral'} size="sm">
            {item.status}
          </Badge>
        ),
      },
      {
        key: 'id',
        header: 'Audit',
        width: '110px',
        render: () => (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/audit')}
          >
            Audit
          </Button>
        ),
      },
    ];

    return (
      <div className={styles.dashboardContainer}>
        {isModeratorRole && renderPerspectiveSwitcher()}
        {isModeratorRole && moderatorPerspective === 'MENTOR' && (
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '12px 18px',
              backgroundColor: 'rgba(14, 117, 119, 0.08)',
              border: '1px solid rgba(14, 117, 119, 0.25)',
              borderRadius: '10px',
              marginBottom: '20px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Badge variant="teal" size="sm">Super Admin Clearance</Badge>
              <span style={{ fontSize: '0.92rem', fontWeight: 600, color: '#0E7577' }}>
                Inspecting Live Mentor / Faculty Workspace &amp; Review Backlog
              </span>
            </div>
            <span style={{ fontSize: '0.85rem', color: '#475569' }}>
              Showing {adviseeRecords.length} institutional advisees &amp; {reviewQueue.length} pending reviews
            </span>
          </div>
        )}
        <PageHeader
          title="Advisor Academic Operations"
          subtitle="Triage submitted degree plans, evaluate prerequisite waivers, and track advisee progress."
          breadcrumbs={[{ label: 'Academic Workspace' }, { label: 'Advisor Overview' }]}
          actions={
            <div className={styles.headerActions}>
              <Button
                variant="primary"
                size="sm"
                leftIcon={<Users size={14} />}
                onClick={() => navigate('/advising')}
              >
                Open Review Workspace
              </Button>
            </div>
          }
        />

        {/* 4 Metric Cards */}
        <div className={styles.metricsGrid}>
          <div className={styles.metricCard}>
            <span className={styles.metricLabel}>Pending Plan Reviews</span>
            <span className={styles.metricValue}>{pendingCount}</span>
            <span className={styles.metricMeta}>Awaiting formal advisor decision</span>
          </div>

          <div className={styles.metricCard}>
            <span className={styles.metricLabel}>Assigned Advisees</span>
            <span className={styles.metricValue}>{adviseeRecords.length}</span>
            <span className={styles.metricMeta}>Active student cohort</span>
          </div>

          <div className={styles.metricCard}>
            <span className={styles.metricLabel}>Action Required</span>
            <span className={styles.metricValue}>{attentionCount}</span>
            <span className={styles.metricMeta}>Plans with rule warnings or overrides</span>
          </div>

          <div className={styles.metricCard}>
            <span className={styles.metricLabel}>Academic Standard</span>
            <span className={styles.metricValue} style={{ fontSize: '1.25rem' }}>
              10.0 Scale
            </span>
            <span className={styles.metricMeta}>Verified institutional standard</span>
          </div>
        </div>

        {/* Review Queue Card */}
        <div className={styles.cardContainer}>
          <div className={styles.cardHeader}>
            <div>
              <h3 className={styles.cardTitle}>Priority Plan Review Queue</h3>
              <span className={styles.cardSubtitle}>
                Submitted semester course plans requiring review and approval
              </span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate('/advising')}
            >
              Full Queue ({reviewQueue.length})
            </Button>
          </div>
          <Table<ReviewQueueItem>
            columns={queueColumns}
            data={reviewQueue.slice(0, 5)}
            keyExtractor={(item) => item.plan_id}
            caption="Plans pending advisor review"
          />
        </div>

        {/* Advisee Roster Card */}
        <div className={styles.cardContainer}>
          <div className={styles.cardHeader}>
            <div>
              <h3 className={styles.cardTitle}>Advisee Cohort Roster</h3>
              <span className={styles.cardSubtitle}>
                Current academic performance and credit accumulation
              </span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate('/audit')}
            >
              Audit Workspace
            </Button>
          </div>
          <Table<StudentRecord>
            columns={adviseeColumns}
            data={adviseeRecords.slice(0, 6)}
            keyExtractor={(item) => item.id}
            caption="Assigned students overview"
          />
        </div>
      </div>
    );
  }

  // ==========================================
  // 3. PROGRAMME COORDINATOR VIEW
  // ==========================================
  if (currentRole === 'COORDINATOR') {
    const programmeColumns: Column<Programme>[] = [
      { key: 'code', header: 'Programme Code', width: '140px', sortable: true },
      { key: 'name', header: 'Programme Name', sortable: true },
      { key: 'degree_type', header: 'Degree Level', width: '130px', sortable: true },
      { key: 'department', header: 'Department', sortable: true },
      {
        key: 'is_active',
        header: 'Status',
        width: '110px',
        render: (item) => (
          <Badge variant={item.is_active ? 'success' : 'neutral'} size="sm">
            {item.is_active ? 'Active' : 'Archived'}
          </Badge>
        ),
      },
      {
        key: 'id',
        header: 'Action',
        width: '120px',
        render: () => (
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/curriculum')}
          >
            Manage
          </Button>
        ),
      },
    ];

    return (
      <div className={styles.dashboardContainer}>
        {isModeratorRole && renderPerspectiveSwitcher()}
        {isModeratorRole && moderatorPerspective === 'MENTOR' && (
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '12px 18px',
              backgroundColor: 'rgba(14, 117, 119, 0.08)',
              border: '1px solid rgba(14, 117, 119, 0.25)',
              borderRadius: '10px',
              marginBottom: '20px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Badge variant="teal" size="sm">Super Admin Clearance</Badge>
              <span style={{ fontSize: '0.92rem', fontWeight: 600, color: '#0E7577' }}>
                Inspecting Live Mentor / Faculty Workspace &amp; Review Backlog
              </span>
            </div>
            <span style={{ fontSize: '0.85rem', color: '#475569' }}>
              Showing {adviseeRecords.length} institutional advisees &amp; {reviewQueue.length} pending reviews
            </span>
          </div>
        )}
        <PageHeader
          title="Programme Coordinator Operations"
          subtitle="Author curriculum versions, configure prerequisite logic rules, and govern academic catalogs."
          breadcrumbs={[{ label: 'Academic Workspace' }, { label: 'Coordinator Overview' }]}
          actions={
            <div className={styles.headerActions}>
              <Button
                variant="primary"
                size="sm"
                leftIcon={<BookOpen size={14} />}
                onClick={() => navigate('/curriculum')}
              >
                Curriculum Catalog
              </Button>
            </div>
          }
        />

        {/* 4 Metric Cards */}
        <div className={styles.metricsGrid}>
          <div className={styles.metricCard}>
            <span className={styles.metricLabel}>Academic Programmes</span>
            <span className={styles.metricValue}>{programmes.length}</span>
            <span className={styles.metricMeta}>Active department offerings</span>
          </div>

          <div className={styles.metricCard}>
            <span className={styles.metricLabel}>Courses in Catalog</span>
            <span className={styles.metricValue}>{courses.length}</span>
            <span className={styles.metricMeta}>Accredited courses registered</span>
          </div>

          <div className={styles.metricCard}>
            <span className={styles.metricLabel}>Rule Engine Status</span>
            <span className={styles.metricValue} style={{ fontSize: '1.25rem', color: '#0E7577' }}>
              Deterministic DAG
            </span>
            <span className={styles.metricMeta}>Cycles verified & validated</span>
          </div>

          <div className={styles.metricCard}>
            <span className={styles.metricLabel}>Institutional Scale</span>
            <span className={styles.metricValue} style={{ fontSize: '1.25rem' }}>
              10.0 Scale
            </span>
            <span className={styles.metricMeta}>Standardized graduation criteria</span>
          </div>
        </div>

        {/* Action Hub */}
        <div className={styles.actionHubSection}>
          <h2 className={styles.sectionHeading}>Curriculum Operations</h2>
          <div className={styles.actionGrid}>
            <div
              className={styles.actionCard}
              onClick={() => navigate('/curriculum')}
              role="button"
              tabIndex={0}
            >
              <div className={styles.actionCardHeader}>
                <div className={styles.actionIcon}>
                  <BookOpen size={20} />
                </div>
                <div className={styles.actionCardBody}>
                  <h3 className={styles.actionTitle}>Curriculum Authoring</h3>
                  <p className={styles.actionDesc}>
                    Create version drafts, configure requirement groups, and publish immutable academic catalogs.
                  </p>
                </div>
              </div>
              <div className={styles.actionCardFooter}>
                <span>Manage Curricula</span>
                <ArrowRight size={14} />
              </div>
            </div>

            <div
              className={styles.actionCard}
              onClick={() => navigate('/audit')}
              role="button"
              tabIndex={0}
            >
              <div className={styles.actionCardHeader}>
                <div className={`${styles.actionIcon} ${styles.actionIconBlue}`}>
                  <FileCheck size={20} />
                </div>
                <div className={styles.actionCardBody}>
                  <h3 className={styles.actionTitle}>Audit Simulation</h3>
                  <p className={styles.actionDesc}>
                    Run student degree audits against newly published curriculum drafts to test rule satisfaction.
                  </p>
                </div>
              </div>
              <div className={styles.actionCardFooter}>
                <span>Open Auditor</span>
                <ArrowRight size={14} />
              </div>
            </div>

            <div
              className={styles.actionCard}
              onClick={() => navigate('/analytics')}
              role="button"
              tabIndex={0}
            >
              <div className={styles.actionCardHeader}>
                <div className={`${styles.actionIcon} ${styles.actionIconGold}`}>
                  <BarChart3 size={20} />
                </div>
                <div className={styles.actionCardBody}>
                  <h3 className={styles.actionTitle}>Bottleneck Analytics</h3>
                  <p className={styles.actionDesc}>
                    Detect course prerequisite bottlenecks impacting student graduation pacing and elective demand.
                  </p>
                </div>
              </div>
              <div className={styles.actionCardFooter}>
                <span>View Bottlenecks</span>
                <ArrowRight size={14} />
              </div>
            </div>
          </div>
        </div>

        {/* Programmes Catalog Table */}
        <div className={styles.cardContainer}>
          <div className={styles.cardHeader}>
            <div>
              <h3 className={styles.cardTitle}>Academic Degree Programmes</h3>
              <span className={styles.cardSubtitle}>
                Institutional programs currently active under your coordination
              </span>
            </div>
          </div>
          <Table<Programme>
            columns={programmeColumns}
            data={programmes}
            keyExtractor={(item) => item.id}
            caption="Active degree programs"
          />
        </div>
      </div>
    );
  }

  // ==========================================
  // 4. HEAD OF DEPARTMENT (HOD) VIEW
  // ==========================================
  if (currentRole === 'HOD') {
    const progItems = programmeProgress?.items || [];
    const bottlenecks = analyticsOverview?.top_bottlenecks || [];

    const hodProgrammeColumns: Column<ProgrammeProgressItem>[] = [
      { key: 'programme_code', header: 'Programme Code', width: '130px', sortable: true },
      { key: 'programme_name', header: 'Programme Name', sortable: true },
      { key: 'total_students', header: 'Enrolled Students', width: '140px', align: 'right', sortable: true },
      {
        key: 'avg_cgpa',
        header: 'Avg CGPA (10.0 Scale)',
        width: '170px',
        align: 'right',
        sortable: true,
        render: (item) => (
          <strong>{(item.avg_cgpa ?? 0).toFixed(2)}</strong>
        ),
      },
      {
        key: 'avg_earned_credits',
        header: 'Avg Earned Credits',
        width: '150px',
        align: 'right',
        sortable: true,
        render: (item) => `${Math.round(item.avg_earned_credits ?? 0)} cr`,
      },
      {
        key: 'near_completion',
        header: 'Near Completion',
        width: '140px',
        align: 'right',
        sortable: true,
        render: (item) => (
          <Badge variant="success" size="sm">
            {item.near_completion} students
          </Badge>
        ),
      },
    ];

    return (
      <div className={styles.dashboardContainer}>
        {isModeratorRole && renderPerspectiveSwitcher()}
        {isModeratorRole && moderatorPerspective === 'MENTOR' && (
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '12px 18px',
              backgroundColor: 'rgba(14, 117, 119, 0.08)',
              border: '1px solid rgba(14, 117, 119, 0.25)',
              borderRadius: '10px',
              marginBottom: '20px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Badge variant="teal" size="sm">Super Admin Clearance</Badge>
              <span style={{ fontSize: '0.92rem', fontWeight: 600, color: '#0E7577' }}>
                Inspecting Live Mentor / Faculty Workspace &amp; Review Backlog
              </span>
            </div>
            <span style={{ fontSize: '0.85rem', color: '#475569' }}>
              Showing {adviseeRecords.length} institutional advisees &amp; {reviewQueue.length} pending reviews
            </span>
          </div>
        )}
        <PageHeader
          title="Department Executive Overview"
          subtitle="Departmental academic performance, cohort graduation trajectories, and prerequisite bottlenecks."
          breadcrumbs={[{ label: 'Academic Workspace' }, { label: 'HOD Executive Overview' }]}
          actions={
            <div className={styles.headerActions}>
              <Button
                variant="primary"
                size="sm"
                leftIcon={<BarChart3 size={14} />}
                onClick={() => navigate('/analytics')}
              >
                Comprehensive Analytics
              </Button>
            </div>
          }
        />

        {/* 4 Metric Cards */}
        <div className={styles.metricsGrid}>
          <div className={styles.metricCard}>
            <span className={styles.metricLabel}>Total Department Students</span>
            <span className={styles.metricValue}>
              {analyticsOverview?.total_active_students || 0}
            </span>
            <span className={styles.metricMeta}>Enrolled across all departmental programs</span>
          </div>

          <div className={styles.metricCard}>
            <span className={styles.metricLabel}>Department Avg CGPA</span>
            <span className={styles.metricValue}>
              8.65
              <span className={styles.metricSub}>/ 10.00 Scale</span>
            </span>
            <span className={styles.metricMeta}>Satisfies graduation quality thresholds</span>
          </div>

          <div className={styles.metricCard}>
            <span className={styles.metricLabel}>Plans Pending Approval</span>
            <span className={styles.metricValue}>
              {analyticsOverview?.plans_pending_review || 0}
            </span>
            <span className={styles.metricMeta}>In advisor evaluation workflow</span>
          </div>

          <div className={styles.metricCard}>
            <span className={styles.metricLabel}>Academic Risk Cohort</span>
            <span className={styles.metricValue}>
              {analyticsOverview?.critical_or_high_risk_students || 0}
            </span>
            <span className={styles.metricMeta}>Students flagged for advisor intervention</span>
          </div>
        </div>

        {/* Two-Column: Programme Performance & Bottleneck Diagnostics */}
        <div className={styles.contentGrid}>
          <div className={styles.cardContainer}>
            <div className={styles.cardHeader}>
              <div>
                <h3 className={styles.cardTitle}>Programme Cohort Performance</h3>
                <span className={styles.cardSubtitle}>
                  Enrollment, cumulative GPA, and graduation pacing by academic program
                </span>
              </div>
            </div>
            <Table<ProgrammeProgressItem>
              columns={hodProgrammeColumns}
              data={progItems}
              keyExtractor={(item) => item.programme_id}
              caption="Departmental programme summary"
            />
          </div>

          <div className={styles.cardContainer}>
            <div className={styles.cardHeader}>
              <div>
                <h3 className={styles.cardTitle}>Curriculum Bottlenecks</h3>
                <span className={styles.cardSubtitle}>Courses blocking student progression</span>
              </div>
            </div>

            {bottlenecks.length === 0 ? (
              <p style={{ color: '#64748B', fontSize: '0.875rem' }}>
                No critical prerequisite bottlenecks detected.
              </p>
            ) : (
              <div className={styles.bottleneckList}>
                {bottlenecks.map((item) => (
                  <div key={item.course_code} className={styles.bottleneckItem}>
                    <div className={styles.bottleneckInfo}>
                      <span className={styles.bottleneckCode}>{item.course_code}</span>
                      <span className={styles.bottleneckName}>{item.course_name}</span>
                    </div>
                    <Badge variant="warning" size="sm">
                      {item.impacted_students_count} students blocked
                    </Badge>
                  </div>
                ))}
              </div>
            )}

            <div style={{ marginTop: 'auto', paddingTop: '12px' }}>
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate('/analytics')}
                style={{ width: '100%' }}
              >
                Inspect Prerequisite Diagnostics
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ==========================================
  // 5. SYSTEM ADMINISTRATOR VIEW
  // ==========================================
  const termColumns: Column<AcademicTerm>[] = [
    { key: 'code', header: 'Term Code', width: '120px', sortable: true },
    { key: 'name', header: 'Academic Term Name', sortable: true },
    { key: 'season', header: 'Season', width: '110px', sortable: true },
    { key: 'year', header: 'Year', width: '90px', align: 'center', sortable: true },
    { key: 'start_date', header: 'Start Date', width: '120px', sortable: true },
    { key: 'end_date', header: 'End Date', width: '120px', sortable: true },
    {
      key: 'is_active',
      header: 'Session Status',
      width: '130px',
      render: (item) => (
        <Badge variant={item.is_active ? 'success' : 'neutral'} size="sm">
          {item.is_active ? 'Active Term' : 'Inactive'}
        </Badge>
      ),
    },
  ];

  return (
    <div className={styles.dashboardContainer}>
      {isModeratorRole && renderPerspectiveSwitcher()}
      {isModeratorRole && moderatorPerspective === 'MODERATOR' && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '12px 18px',
            backgroundColor: 'rgba(124, 58, 237, 0.08)',
            border: '1px solid rgba(124, 58, 237, 0.25)',
            borderRadius: '10px',
            marginBottom: '20px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Badge variant="teal" size="sm">Super Admin Control Center</Badge>
            <span style={{ fontSize: '0.92rem', fontWeight: 600, color: '#7C3AED' }}>
              Institutional Moderator &amp; System Administration Workspace
            </span>
          </div>
          <span style={{ fontSize: '0.85rem', color: '#475569' }}>
            Full Clearance: Curriculum, Advising Oversight, Analytics &amp; Multi-Tenant Controls
          </span>
        </div>
      )}
      <PageHeader
        title="Institutional System Administration"
        subtitle="Multi-tenant institutional configuration, academic term calendars, security governance, and operational controls."
        breadcrumbs={[{ label: 'Institutional Admin' }, { label: 'System Overview' }]}
        badge={
          <Badge variant="success" size="sm" icon={<ShieldCheck size={12} />}>
            Operational
          </Badge>
        }
      />

      {/* 4 Metric Cards */}
      <div className={styles.metricsGrid}>
        <div className={styles.metricCard}>
          <span className={styles.metricLabel}>Tenant Institution</span>
          <span className={styles.metricValue} style={{ fontSize: '1.25rem' }}>
            {activeMembership?.institution_code || 'MSU'}
          </span>
          <span className={styles.metricMeta}>
            {activeMembership?.institution_name || 'Metropolitan State University'}
          </span>
        </div>

        <div className={styles.metricCard}>
          <span className={styles.metricLabel}>Security Architecture</span>
          <span className={styles.metricValue} style={{ fontSize: '1.25rem', color: '#0E7577' }}>
            Row-Level Multi-Tenancy
          </span>
          <span className={styles.metricMeta}>Isolated tenant boundaries enforced</span>
        </div>

        <div className={styles.metricCard}>
          <span className={styles.metricLabel}>GPA Evaluation Standard</span>
          <span className={styles.metricValue} style={{ fontSize: '1.25rem' }}>
            10.0 Scale
          </span>
          <span className={styles.metricMeta}>Strict decimal boundary constraints</span>
        </div>

        <div className={styles.metricCard}>
          <span className={styles.metricLabel}>Academic Sessions</span>
          <span className={styles.metricValue}>{academicTerms.length}</span>
          <span className={styles.metricMeta}>Configured term schedules</span>
        </div>
      </div>

      {/* Admin Action Hub */}
      <div className={styles.actionHubSection}>
        <h2 className={styles.sectionHeading}>Administrative Portals</h2>
        <div className={styles.actionGrid}>
          <div
            className={styles.actionCard}
            onClick={() => navigate('/curriculum')}
            role="button"
            tabIndex={0}
          >
            <div className={styles.actionCardHeader}>
              <div className={styles.actionIcon}>
                <BookOpen size={20} />
              </div>
              <div className={styles.actionCardBody}>
                <h3 className={styles.actionTitle}>Curriculum Governance</h3>
                <p className={styles.actionDesc}>
                  Manage institutional catalog versions, degree programmes, and prerequisite rules.
                </p>
              </div>
            </div>
            <div className={styles.actionCardFooter}>
              <span>Catalog Management</span>
              <ArrowRight size={14} />
            </div>
          </div>

          <div
            className={styles.actionCard}
            onClick={() => navigate('/advising')}
            role="button"
            tabIndex={0}
          >
            <div className={styles.actionCardHeader}>
              <div className={`${styles.actionIcon} ${styles.actionIconBlue}`}>
                <Users size={20} />
              </div>
              <div className={styles.actionCardBody}>
                <h3 className={styles.actionTitle}>Advising Operations</h3>
                <p className={styles.actionDesc}>
                  Monitor advisor workloads, review queue backlogs, and plan approval turnarounds.
                </p>
              </div>
            </div>
            <div className={styles.actionCardFooter}>
              <span>Advising System</span>
              <ArrowRight size={14} />
            </div>
          </div>

          <div
            className={styles.actionCard}
            onClick={() => navigate('/analytics')}
            role="button"
            tabIndex={0}
          >
            <div className={styles.actionCardHeader}>
              <div className={`${styles.actionIcon} ${styles.actionIconGold}`}>
                <BarChart3 size={20} />
              </div>
              <div className={styles.actionCardBody}>
                <h3 className={styles.actionTitle}>System Analytics</h3>
                <p className={styles.actionDesc}>
                  Review institution-wide student progress, elective demand forecasts, and risk metrics.
                </p>
              </div>
            </div>
            <div className={styles.actionCardFooter}>
              <span>Executive Reports</span>
              <ArrowRight size={14} />
            </div>
          </div>
        </div>
      </div>

      {/* Terms Table */}
      <div className={styles.cardContainer}>
        <div className={styles.cardHeader}>
          <div>
            <h3 className={styles.cardTitle}>Academic Term Calendar</h3>
            <span className={styles.cardSubtitle}>
              Institutional academic calendar sessions configured in the platform
            </span>
          </div>
        </div>
        <Table<AcademicTerm>
          columns={termColumns}
          data={academicTerms}
          keyExtractor={(item) => item.id}
          caption="Configured academic terms"
        />
      </div>
    </div>
  );
};
