import React, { useState, useMemo } from 'react';
import {
  Activity,
  CalendarCheck,
  CheckCircle2,
  Clock,
  Info,
  Sparkles,
} from 'lucide-react';
import styles from './DashboardPage.module.css';
import {
  PageHeader,
  Button,
  Badge,
  Table,
  Column,
  Tabs,
  TabItem,
  Dialog,
  Toast,
  ToastProps,
  Input,
} from '../components';
import {
  DEMO_STUDENT_SUMMARY,
  DEMO_COURSES,
  DEMO_PROGRAM_GROUPS,
  DemoCourseItem,
} from '../fixtures/demoData';
import { apiClient } from '../api/client';

export const DashboardPage: React.FC = () => {
  // Tabs State
  const [activeTab, setActiveTab] = useState('courses');

  // Table Sorting State
  const [sortColumn, setSortColumn] = useState<string>('code');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  // Dialog State
  const [isConsultationOpen, setIsConsultationOpen] = useState(false);
  const [consultationReason, setConsultationReason] = useState(
    'Discuss upcoming semester course plan and prereq waivers.'
  );

  // Toast Notification State
  const [toasts, setToasts] = useState<Omit<ToastProps, 'onClose'>[]>([]);

  // Health API Trigger State
  const [isCheckingHealth, setIsCheckingHealth] = useState(false);

  const addToast = (toast: Omit<ToastProps, 'onClose' | 'id'>) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { ...toast, id }]);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const handleTestHealth = async () => {
    setIsCheckingHealth(true);
    try {
      const res = await apiClient.checkHealth();
      addToast({
        type: 'success',
        title: 'Backend Health Check OK',
        message: `Service: ${res.service} (v${res.version}) at ${new Date(res.timestamp).toLocaleTimeString()}`,
      });
    } catch (err) {
      addToast({
        type: 'danger',
        title: 'Backend Connection Failed',
        message: err instanceof Error ? err.message : 'Unknown error',
      });
    } finally {
      setIsCheckingHealth(false);
    }
  };

  const handleConsultationSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsConsultationOpen(false);
    addToast({
      type: 'info',
      title: 'Advisor Consultation Requested',
      message: 'Your meeting request has been recorded for Dr. Eleanor Vance.',
    });
  };

  const handleSort = (columnKey: string) => {
    if (sortColumn === columnKey) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortColumn(columnKey);
      setSortDirection('asc');
    }
  };

  // Sorted Courses Memo
  const sortedCourses = useMemo(() => {
    const list = [...DEMO_COURSES];
    list.sort((a, b) => {
      const aVal = a[sortColumn as keyof DemoCourseItem];
      const bVal = b[sortColumn as keyof DemoCourseItem];
      if (typeof aVal === 'string') {
        return sortDirection === 'asc'
          ? (aVal as string).localeCompare(bVal as string)
          : (bVal as string).localeCompare(aVal as string);
      }
      if (typeof aVal === 'number') {
        return sortDirection === 'asc'
          ? (aVal as number) - (bVal as number)
          : (bVal as number) - (aVal as number);
      }
      return 0;
    });
    return list;
  }, [sortColumn, sortDirection]);

  // Course Columns Definition
  const courseColumns: Column<DemoCourseItem>[] = [
    { key: 'code', header: 'Course Code', sortable: true, width: '130px' },
    { key: 'title', header: 'Course Title', sortable: true },
    { key: 'credits', header: 'Credits', sortable: true, width: '90px', align: 'center' },
    { key: 'term', header: 'Term', sortable: true, width: '130px' },
    { key: 'grade', header: 'Grade', sortable: true, width: '80px', align: 'center' },
    {
      key: 'status',
      header: 'Status',
      width: '140px',
      render: (item) => {
        if (item.status === 'COMPLETED') {
          return (
            <Badge variant="success" size="sm" icon={<CheckCircle2 size={12} />}>
              Completed
            </Badge>
          );
        }
        if (item.status === 'IN_PROGRESS') {
          return (
            <Badge variant="teal" size="sm" icon={<Clock size={12} />}>
              In Progress
            </Badge>
          );
        }
        return (
          <Badge variant="neutral" size="sm">
            Planned
          </Badge>
        );
      },
    },
  ];

  const tabs: TabItem[] = [
    { id: 'courses', label: 'Course History', count: DEMO_COURSES.length },
    { id: 'requirements', label: 'Requirement Groups', count: DEMO_PROGRAM_GROUPS.length },
    { id: 'rules', label: 'Rule Engine Principles' },
  ];

  return (
    <div className={styles.dashboardContainer}>
      {/* Page Header */}
      <PageHeader
        title="Student Degree Progress & Audit"
        subtitle="Authoritative progress evaluated against pinned curriculum catalog 2024–2025"
        badge={
          <Badge variant="teal" size="sm">
            Demo Data Fixture
          </Badge>
        }
        breadcrumbs={[
          { label: 'Academic Workspace', href: '/dashboard' },
          { label: 'Degree Audit' },
        ]}
        actions={
          <div className={styles.headerActions}>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<Activity size={14} />}
              isLoading={isCheckingHealth}
              onClick={handleTestHealth}
            >
              Verify API Health
            </Button>
            <Button
              variant="primary"
              size="sm"
              leftIcon={<CalendarCheck size={14} />}
              onClick={() => setIsConsultationOpen(true)}
            >
              Consult Advisor
            </Button>
          </div>
        }
      />

      {/* Demo Notice Banner */}
      <div className={styles.demoBanner}>
        <Info size={16} className={styles.bannerIcon} />
        <div>
          <strong>Phase 01 Shell Preview:</strong> Academic figures below are sourced from{' '}
          <code>fixtures/demoData.ts</code>. Authoritative calculation engine will activate in Phase 05.
        </div>
      </div>

      {/* Metric Cards Row */}
      <div className={styles.metricsGrid}>
        <div className={styles.metricCard}>
          <span className={styles.metricLabel}>Assigned Program</span>
          <span className={styles.metricValue}>{DEMO_STUDENT_SUMMARY.programName}</span>
          <span className={styles.metricMeta}>Catalog Year {DEMO_STUDENT_SUMMARY.catalogYear}</span>
        </div>

        <div className={styles.metricCard}>
          <span className={styles.metricLabel}>Credits Earned</span>
          <span className={styles.metricValue}>
            {DEMO_STUDENT_SUMMARY.creditsEarned}{' '}
            <span className={styles.metricSub}>/ {DEMO_STUDENT_SUMMARY.totalCreditsRequired}</span>
          </span>
          <span className={styles.metricMeta}>
            +{DEMO_STUDENT_SUMMARY.creditsInProgress} credits in progress
          </span>
        </div>

        <div className={styles.metricCard}>
          <span className={styles.metricLabel}>Cumulative GPA</span>
          <span className={styles.metricValue}>{DEMO_STUDENT_SUMMARY.cumulativeGpa}</span>
          <span className={styles.metricMeta}>Calculated with standard Decimal precision</span>
        </div>

        <div className={styles.metricCard}>
          <span className={styles.metricLabel}>Assigned Faculty Advisor</span>
          <span className={styles.metricValue}>{DEMO_STUDENT_SUMMARY.advisorName}</span>
          <span className={styles.metricMeta}>{DEMO_STUDENT_SUMMARY.advisorEmail}</span>
        </div>
      </div>

      {/* Main Tabbed Data Area */}
      <div className={styles.tabSection}>
        <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab}>
          {activeTab === 'courses' && (
            <div className={styles.tabContent}>
              <Table<DemoCourseItem>
                columns={courseColumns}
                data={sortedCourses}
                keyExtractor={(item) => item.id}
                sortColumn={sortColumn}
                sortDirection={sortDirection}
                onSort={handleSort}
                caption="Enrolled & Completed Courses"
              />
            </div>
          )}

          {activeTab === 'requirements' && (
            <div className={styles.tabContent}>
              <div className={styles.requirementsList}>
                {DEMO_PROGRAM_GROUPS.map((grp) => (
                  <div key={grp.id} className={styles.requirementItem}>
                    <div className={styles.requirementHeader}>
                      <span className={styles.requirementName}>{grp.name}</span>
                      <span className={styles.requirementCredits}>
                        {grp.completedCredits} / {grp.requiredCredits} credits
                      </span>
                    </div>
                    <div className={styles.progressBarBg}>
                      <div
                        className={styles.progressBarFill}
                        style={{
                          width: `${Math.min(100, (grp.completedCredits / grp.requiredCredits) * 100)}%`,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'rules' && (
            <div className={styles.tabContent}>
              <div className={styles.rulesExplainer}>
                <h3 className={styles.rulesTitle}>Prerequisite Interpreter Architecture</h3>
                <p className={styles.rulesText}>
                  The upcoming Phase 03 rule engine interprets Boolean combinations of course
                  prerequisites, minimum grade constraints, corequisites, and credit thresholds.
                </p>
                <div className={styles.ruleHighlights}>
                  <div className={styles.highlightItem}>
                    <Sparkles size={16} className={styles.highlightIcon} />
                    <span>Pure Python interpreter with zero external Django ORM dependencies.</span>
                  </div>
                  <div className={styles.highlightItem}>
                    <Sparkles size={16} className={styles.highlightIcon} />
                    <span>Deterministic evaluation with Kleene three-valued logic.</span>
                  </div>
                  <div className={styles.highlightItem}>
                    <Sparkles size={16} className={styles.highlightIcon} />
                    <span>Exact actionable deficiency reporting for students and advisors.</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </Tabs>
      </div>

      {/* Consultation Dialog */}
      <Dialog
        isOpen={isConsultationOpen}
        onClose={() => setIsConsultationOpen(false)}
        title="Schedule Advisor Consultation"
        description="Book a degree planning session with your designated advisor."
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
              Submit Request
            </Button>
          </>
        }
      >
        <form onSubmit={handleConsultationSubmit} className={styles.dialogForm}>
          <Input
            label="Advisor"
            value={DEMO_STUDENT_SUMMARY.advisorName}
            disabled
          />
          <Input
            label="Reason for Consultation"
            value={consultationReason}
            onChange={(e) => setConsultationReason(e.target.value)}
            required
          />
          <p className={styles.dialogNotice}>
            Your advisor will be notified and will review your simulated multi-semester plan before
            confirming the appointment.
          </p>
        </form>
      </Dialog>

      {/* Toast Notification Container */}
      <div className={styles.toastContainer} aria-live="polite">
        {toasts.map((toast) => (
          <Toast key={toast.id} {...toast} onClose={removeToast} />
        ))}
      </div>
    </div>
  );
};
