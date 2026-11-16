import React, { useState, useEffect, useCallback } from 'react';
import {
  Users,
  Clock,
  AlertTriangle,
  FileSpreadsheet,
  Download,
  RefreshCw,
  Layers,
  ShieldAlert,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { PageHeader } from '../components/PageHeader/PageHeader';
import { Tabs, TabItem } from '../components/Tabs/Tabs';
import { Table, Column } from '../components/Table/Table';
import { Button } from '../components/Button/Button';
import { Badge } from '../components/Badge/Badge';
import { Skeleton } from '../components/Skeleton/Skeleton';
import { ErrorState } from '../components/ErrorState/ErrorState';
import { EmptyState } from '../components/EmptyState/EmptyState';
import {
  analyticsApi,
  AnalyticsOverview,
  ProgrammeProgressReport,
  ProgrammeProgressItem,
  PrerequisiteBlockersReport,
  PrerequisiteBlockerItem,
  AdvisorWorkloadReport,
  AdvisorWorkloadItem,
  ApprovalTurnaroundReport,
  ReviewerTurnaroundItem,
  PlanFunnelReport,
  RiskDistributionReport,
  ProgrammeRiskBreakdown,
  ElectiveDemandReport,
  ElectiveDemandItem,
} from '../api/analytics';
import styles from './AnalyticsDashboardPage.module.css';

const TABS: TabItem[] = [
  { id: 'progress', label: 'Degree Progress' },
  { id: 'blockers', label: 'Prerequisite Blockers' },
  { id: 'workload', label: 'Advisor Workload' },
  { id: 'turnaround', label: 'Turnaround Times' },
  { id: 'funnel', label: 'Plan Funnel' },
  { id: 'risk', label: 'Graduation Risk' },
  { id: 'demand', label: 'Elective Demand' },
];

export const AnalyticsDashboardPage: React.FC = () => {
  const { activeRole } = useAuth();
  const [activeTab, setActiveTab] = useState<string>('progress');

  // Executive Overview State
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [isOverviewLoading, setIsOverviewLoading] = useState(true);
  const [overviewError, setOverviewError] = useState<string | null>(null);

  // Tab Report States
  const [progressReport, setProgressReport] = useState<ProgrammeProgressReport | null>(null);
  const [blockersReport, setBlockersReport] = useState<PrerequisiteBlockersReport | null>(null);
  const [workloadReport, setWorkloadReport] = useState<AdvisorWorkloadReport | null>(null);
  const [turnaroundReport, setTurnaroundReport] = useState<ApprovalTurnaroundReport | null>(null);
  const [funnelReport, setFunnelReport] = useState<PlanFunnelReport | null>(null);
  const [riskReport, setRiskReport] = useState<RiskDistributionReport | null>(null);
  const [demandReport, setDemandReport] = useState<ElectiveDemandReport | null>(null);

  const [isReportLoading, setIsReportLoading] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);

  // Filters
  const [startDateFilter, setStartDateFilter] = useState('');
  const [endDateFilter, setEndDateFilter] = useState('');

  // 1. Load Overview Summary
  const loadOverview = useCallback(async () => {
    setIsOverviewLoading(true);
    setOverviewError(null);
    try {
      const data = await analyticsApi.getOverview();
      setOverview(data);
    } catch {
      setOverviewError('Failed to load institutional overview summary.');
    } finally {
      setIsOverviewLoading(false);
    }
  }, []);

  // 2. Load Report Data based on active tab
  const loadActiveReport = useCallback(async () => {
    setIsReportLoading(true);
    setReportError(null);
    try {
      switch (activeTab) {
        case 'progress': {
          const res = await analyticsApi.getProgrammeProgress();
          setProgressReport(res);
          break;
        }
        case 'blockers': {
          const res = await analyticsApi.getPrerequisiteBlockers({ limit: 25 });
          setBlockersReport(res);
          break;
        }
        case 'workload': {
          const res = await analyticsApi.getAdvisorWorkload();
          setWorkloadReport(res);
          break;
        }
        case 'turnaround': {
          const params: { start_date?: string; end_date?: string } = {};
          if (startDateFilter) params.start_date = startDateFilter;
          if (endDateFilter) params.end_date = endDateFilter;
          const res = await analyticsApi.getApprovalTurnaround(params);
          setTurnaroundReport(res);
          break;
        }
        case 'funnel': {
          const res = await analyticsApi.getPlanFunnel();
          setFunnelReport(res);
          break;
        }
        case 'risk': {
          const res = await analyticsApi.getRiskDistribution();
          setRiskReport(res);
          break;
        }
        case 'demand': {
          const res = await analyticsApi.getElectiveDemand({ limit: 30 });
          setDemandReport(res);
          break;
        }
      }
    } catch {
      setReportError(`Failed to load ${activeTab} report data. Please retry.`);
    } finally {
      setIsReportLoading(false);
    }
  }, [activeTab, startDateFilter, endDateFilter]);

  useEffect(() => {
    loadOverview();
  }, [loadOverview]);

  useEffect(() => {
    loadActiveReport();
  }, [loadActiveReport]);

  const handleExportCsv = (endpoint: string, params?: Record<string, string | number | boolean>) => {
    const url = analyticsApi.getExportUrl(endpoint, params);
    window.open(url, '_blank');
  };

  if (activeRole === 'STUDENT') {
    return (
      <div className={styles.pageContainer}>
        <PageHeader
          title="Institutional Analytics"
          subtitle="Access restricted to advisors, coordinators, and institutional administrators."
        />
        <ErrorState
          title="Access Restricted"
          message="Student accounts are not authorized to view aggregated institutional analytics. Please contact your academic advisor for degree questions."
        />
      </div>
    );
  }

  // Table Columns Definition
  const progressColumns: Column<ProgrammeProgressItem>[] = [
    { key: 'programme_code', header: 'Programme Code', sortable: true },
    { key: 'programme_name', header: 'Programme Name', sortable: true },
    { key: 'total_students', header: 'Enrolled Students', sortable: true, align: 'right' },
    {
      key: 'avg_cgpa',
      header: 'Avg CGPA',
      sortable: true,
      align: 'right',
      render: (item) => (item.avg_cgpa ?? 0).toFixed(2),
    },
    {
      key: 'avg_earned_credits',
      header: 'Avg Earned Credits',
      sortable: true,
      align: 'right',
      render: (item) => (item.avg_earned_credits ?? 0).toFixed(1),
    },
    { key: 'bracket_0_25', header: '0–25%', align: 'center' },
    { key: 'bracket_26_50', header: '26–50%', align: 'center' },
    { key: 'bracket_51_75', header: '51–75%', align: 'center' },
    { key: 'bracket_76_100', header: '76–100%', align: 'center' },
    {
      key: 'near_completion',
      header: 'Near Grad (≥90%)',
      align: 'right',
      render: (item) => (
        <Badge variant={item.near_completion > 0 ? 'success' : 'neutral'}>
          {item.near_completion}
        </Badge>
      ),
    },
  ];

  const blockersColumns: Column<PrerequisiteBlockerItem>[] = [
    { key: 'course_code', header: 'Course Code', sortable: true },
    { key: 'course_name', header: 'Course Name', sortable: true },
    { key: 'credits', header: 'Credits', align: 'center' },
    {
      key: 'impacted_students_count',
      header: 'Impacted Students',
      sortable: true,
      align: 'right',
      render: (item) => (
        <Badge variant="danger">{item.impacted_students_count} students</Badge>
      ),
    },
    {
      key: 'total_unpassed_attempts',
      header: 'Failed/Unpassed Attempts',
      sortable: true,
      align: 'right',
      render: (item) => item.total_unpassed_attempts,
    },
  ];

  const workloadColumns: Column<AdvisorWorkloadItem>[] = [
    { key: 'advisor_name', header: 'Advisor Name', sortable: true },
    { key: 'advisor_username', header: 'Username' },
    { key: 'assigned_advisees_count', header: 'Advisees', sortable: true, align: 'right' },
    {
      key: 'pending_plans_count',
      header: 'Pending Reviews',
      sortable: true,
      align: 'right',
      render: (item) => (
        <Badge variant={item.pending_plans_count > 0 ? 'warning' : 'neutral'}>
          {item.pending_plans_count}
        </Badge>
      ),
    },
    { key: 'completed_reviews_count', header: 'Completed Reviews', sortable: true, align: 'right' },
    {
      key: 'critical_risk_advisees',
      header: 'Critical Risk',
      align: 'right',
      render: (item) => (
        <Badge variant={item.critical_risk_advisees > 0 ? 'danger' : 'neutral'}>
          {item.critical_risk_advisees}
        </Badge>
      ),
    },
    { key: 'high_risk_advisees', header: 'High Risk', align: 'right' },
    { key: 'medium_risk_advisees', header: 'Medium Risk', align: 'right' },
    { key: 'low_risk_advisees', header: 'Low Risk', align: 'right' },
  ];

  const turnaroundColumns: Column<ReviewerTurnaroundItem>[] = [
    { key: 'reviewer_name', header: 'Reviewer / Advisor', sortable: true },
    { key: 'decisions_count', header: 'Total Decisions', sortable: true, align: 'right' },
    {
      key: 'avg_turnaround_hours',
      header: 'Avg Turnaround (Hours)',
      sortable: true,
      align: 'right',
      render: (item) => `${(item.avg_turnaround_hours ?? 0).toFixed(1)} hrs`,
    },
  ];

  const riskColumns: Column<ProgrammeRiskBreakdown>[] = [
    { key: 'programme_code', header: 'Programme Code', sortable: true },
    { key: 'programme_name', header: 'Programme Name', sortable: true },
    { key: 'total_students', header: 'Assessed Students', sortable: true, align: 'right' },
    {
      key: 'critical_risk_count',
      header: 'Critical Risk',
      align: 'right',
      render: (item) => (
        <Badge variant={item.critical_risk_count > 0 ? 'danger' : 'neutral'}>
          {item.critical_risk_count}
        </Badge>
      ),
    },
    {
      key: 'high_risk_count',
      header: 'High Risk',
      align: 'right',
      render: (item) => (
        <Badge variant={item.high_risk_count > 0 ? 'warning' : 'neutral'}>
          {item.high_risk_count}
        </Badge>
      ),
    },
    { key: 'medium_risk_count', header: 'Medium Risk', align: 'right' },
    { key: 'low_risk_count', header: 'Low Risk', align: 'right' },
  ];

  const demandColumns: Column<ElectiveDemandItem>[] = [
    { key: 'course_code', header: 'Course Code', sortable: true },
    { key: 'course_name', header: 'Course Name', sortable: true },
    { key: 'term_code', header: 'Term', sortable: true },
    {
      key: 'student_demand_count',
      header: 'Planned Demand',
      sortable: true,
      align: 'right',
      render: (item) => <strong>{item.student_demand_count}</strong>,
    },
    { key: 'scheduled_capacity', header: 'Capacity', align: 'right' },
    { key: 'currently_enrolled', header: 'Enrolled', align: 'right' },
    {
      key: 'projected_capacity_deficit',
      header: 'Deficit / Shortfall',
      sortable: true,
      align: 'right',
      render: (item) => (
        <Badge variant={item.projected_capacity_deficit > 0 ? 'danger' : 'success'}>
          {item.projected_capacity_deficit > 0
            ? `-${item.projected_capacity_deficit} Seats`
            : 'Sufficient'}
        </Badge>
      ),
    },
  ];

  return (
    <div className={styles.pageContainer}>
      <PageHeader
        title="Institutional Analytics & Reporting"
        subtitle="Authoritative curriculum analytics, graduation progression, advisor workload, and operational metrics."
        badge={<Badge variant="teal">Authorized Institutional Engine</Badge>}
        actions={
          <Button
            variant="outline"
            size="sm"
            leftIcon={<RefreshCw size={14} />}
            onClick={() => {
              loadOverview();
              loadActiveReport();
            }}
          >
            Refresh Metrics
          </Button>
        }
      />

      {/* KPI Overview Grid */}
      {isOverviewLoading ? (
        <div className={styles.kpiGrid}>
          <Skeleton height="96px" />
          <Skeleton height="96px" />
          <Skeleton height="96px" />
          <Skeleton height="96px" />
        </div>
      ) : overviewError ? (
        <ErrorState message={overviewError} onRetry={loadOverview} />
      ) : overview ? (
        <>
          <div className={styles.kpiGrid}>
            <div className={styles.kpiCard}>
              <div className={styles.kpiHeader}>
                <span>Active Students</span>
                <Users size={18} className={styles.kpiIcon} />
              </div>
              <div className={styles.kpiValue}>{overview.total_active_students}</div>
              <div className={styles.kpiSubtext}>Institutional enrolled count</div>
            </div>

            <div className={styles.kpiCard}>
              <div className={styles.kpiHeader}>
                <span>Degree Plans</span>
                <Layers size={18} className={styles.kpiIcon} />
              </div>
              <div className={styles.kpiValue}>{overview.total_plans}</div>
              <div className={styles.kpiSubtext}>
                {overview.plans_pending_review} plans pending advisor review
              </div>
            </div>

            <div className={styles.kpiCard}>
              <div className={styles.kpiHeader}>
                <span>Avg Approval Turnaround</span>
                <Clock size={18} className={styles.kpiIcon} />
              </div>
              <div className={styles.kpiValue}>
                {((overview.avg_turnaround_hours ?? overview.avg_approval_turnaround_hours ?? 0)).toFixed(1)}{' '}
                <span style={{ fontSize: '1rem' }}>hrs</span>
              </div>
              <div className={styles.kpiSubtext}>From submission to advisor decision</div>
            </div>

            <div className={styles.kpiCard}>
              <div className={styles.kpiHeader}>
                <span>Graduation Risk (High/Crit)</span>
                <ShieldAlert size={18} style={{ color: '#ef4444' }} />
              </div>
              <div className={styles.kpiValue} style={{ color: '#ef4444' }}>
                {overview.critical_or_high_risk_students}
              </div>
              <div className={styles.kpiSubtext}>Students requiring active intervention</div>
            </div>
          </div>

          {/* Top Bottlenecks Banner */}
          {overview.top_bottlenecks.length > 0 && (
            <div className={styles.bottlenecksBanner}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <AlertTriangle size={18} />
                <strong>Curriculum Bottleneck Alert:</strong>
              </div>
              <div className={styles.bottleneckList}>
                {overview.top_bottlenecks.map((b) => (
                  <Badge key={b.course_code} variant="danger">
                    {b.course_code} ({b.impacted_students_count} students blocked)
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </>
      ) : null}

      {/* Report Workspace */}
      <div className={styles.reportWorkspace}>
        <Tabs tabs={TABS} activeTab={activeTab} onChange={(id) => setActiveTab(id)} />

        {/* Toolbar with CSV Export */}
        <div className={styles.reportToolbar}>
          <div className={styles.reportMeta}>
            <FileSpreadsheet size={16} />
            <span>
              Report: <strong>{TABS.find((t) => t.id === activeTab)?.label}</strong>
            </span>
          </div>

          <div className={styles.reportActions}>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<Download size={14} />}
              onClick={() => {
                switch (activeTab) {
                  case 'progress':
                    handleExportCsv('programme-progress');
                    break;
                  case 'blockers':
                    handleExportCsv('prerequisite-blockers', { limit: 50 });
                    break;
                  case 'workload':
                    handleExportCsv('advisor-workload');
                    break;
                  case 'turnaround':
                    handleExportCsv('approval-turnaround', {
                      start_date: startDateFilter,
                      end_date: endDateFilter,
                    });
                    break;
                  case 'funnel':
                    handleExportCsv('plan-funnel');
                    break;
                  case 'risk':
                    handleExportCsv('risk-distribution');
                    break;
                  case 'demand':
                    handleExportCsv('elective-demand', { limit: 100 });
                    break;
                }
              }}
            >
              Export CSV
            </Button>
          </div>
        </div>

        {/* Turnaround Date Filter Bar */}
        {activeTab === 'turnaround' && (
          <div className={styles.filtersRow}>
            <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>Filter Decisions:</span>
            <input
              type="date"
              className={styles.filterInput}
              value={startDateFilter}
              onChange={(e) => setStartDateFilter(e.target.value)}
              aria-label="Start date filter"
            />
            <span style={{ fontSize: '0.875rem', color: '#64748b' }}>to</span>
            <input
              type="date"
              className={styles.filterInput}
              value={endDateFilter}
              onChange={(e) => setEndDateFilter(e.target.value)}
              aria-label="End date filter"
            />
            <Button size="sm" variant="secondary" onClick={loadActiveReport}>
              Apply Date Filter
            </Button>
          </div>
        )}

        {/* Content Body */}
        <div className={styles.reportContent}>
          {isReportLoading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <Skeleton height="40px" />
              <Skeleton height="150px" />
              <Skeleton height="200px" />
            </div>
          ) : reportError ? (
            <ErrorState message={reportError} onRetry={loadActiveReport} />
          ) : (
            <>
              {/* Tab 1: Programme Progress */}
              {activeTab === 'progress' && progressReport && (
                <div>
                  <Table
                    columns={progressColumns}
                    data={progressReport.items}
                    keyExtractor={(item) => item.programme_id}
                    caption="Student Degree Progress Distribution by Programme"
                    emptyState={<EmptyState title="No programme data found" />}
                  />
                </div>
              )}

              {/* Tab 2: Prerequisite Blockers */}
              {activeTab === 'blockers' && blockersReport && (
                <div>
                  <Table
                    columns={blockersColumns}
                    data={blockersReport.items}
                    keyExtractor={(item) => item.course_id}
                    caption="High Impact Prerequisite Bottlenecks"
                    emptyState={<EmptyState title="No course bottlenecks identified" />}
                  />
                </div>
              )}

              {/* Tab 3: Advisor Workload */}
              {activeTab === 'workload' && workloadReport && (
                <div>
                  <Table
                    columns={workloadColumns}
                    data={workloadReport.items}
                    keyExtractor={(item) => item.advisor_id}
                    caption="Advisor Workload & Advisee Risk Distribution"
                    emptyState={<EmptyState title="No advisor workloads found" />}
                  />
                </div>
              )}

              {/* Tab 4: Approval Turnaround */}
              {activeTab === 'turnaround' && turnaroundReport && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                  <div className={styles.conversionGrid}>
                    <div className={styles.conversionCard}>
                      <div className={styles.conversionRate}>{turnaroundReport.total_decisions}</div>
                      <div className={styles.conversionLabel}>Total Decisions Made</div>
                    </div>
                    <div className={styles.conversionCard}>
                      <div className={styles.conversionRate}>
                        {(turnaroundReport.avg_turnaround_hours ?? 0).toFixed(1)}h
                      </div>
                      <div className={styles.conversionLabel}>Average Turnaround</div>
                    </div>
                    <div className={styles.conversionCard}>
                      <div className={styles.conversionRate}>
                        {(turnaroundReport.min_turnaround_hours ?? 0).toFixed(1)}h
                      </div>
                      <div className={styles.conversionLabel}>Fastest Decision</div>
                    </div>
                    <div className={styles.conversionCard}>
                      <div className={styles.conversionRate}>
                        {(turnaroundReport.max_turnaround_hours ?? 0).toFixed(1)}h
                      </div>
                      <div className={styles.conversionLabel}>Longest Turnaround</div>
                    </div>
                  </div>

                  <Table
                    columns={turnaroundColumns}
                    data={turnaroundReport.reviewer_breakdown}
                    keyExtractor={(item) => item.reviewer_id}
                    caption="Turnaround Breakdown by Advisor"
                    emptyState={<EmptyState title="No review decisions found in this timeframe" />}
                  />
                </div>
              )}

              {/* Tab 5: Plan Funnel */}
              {activeTab === 'funnel' && funnelReport && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                  <div className={styles.conversionGrid}>
                    <div className={styles.conversionCard}>
                      <div className={styles.conversionRate}>
                        {(funnelReport.conversion_rates?.submission_rate_pct ?? 0).toFixed(1)}%
                      </div>
                      <div className={styles.conversionLabel}>Submission Rate (Draft → Submitted)</div>
                    </div>
                    <div className={styles.conversionCard}>
                      <div className={styles.conversionRate} style={{ color: '#10b981' }}>
                        {(funnelReport.conversion_rates?.approval_rate_pct ?? 0).toFixed(1)}%
                      </div>
                      <div className={styles.conversionLabel}>Approval Rate</div>
                    </div>
                    <div className={styles.conversionCard}>
                      <div className={styles.conversionRate} style={{ color: '#f59e0b' }}>
                        {(funnelReport.conversion_rates?.return_rate_pct ?? 0).toFixed(1)}%
                      </div>
                      <div className={styles.conversionLabel}>Return for Revision Rate</div>
                    </div>
                    <div className={styles.conversionCard}>
                      <div className={styles.conversionRate} style={{ color: '#ef4444' }}>
                        {(funnelReport.conversion_rates?.rejection_rate_pct ?? 0).toFixed(1)}%
                      </div>
                      <div className={styles.conversionLabel}>Rejection Rate</div>
                    </div>
                  </div>

                  <div className={styles.visualCard}>
                    <h4 className={styles.visualTitle}>Plan Pipeline Volume by Status</h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                      {Object.entries(funnelReport.stages).map(([stage, count]) => (
                        <div key={stage} className={styles.progressBarContainer}>
                          <div className={styles.progressBarHeader}>
                            <span style={{ textTransform: 'capitalize' }}>
                              {stage.replace('_', ' ')}
                            </span>
                            <strong>{count} plans</strong>
                          </div>
                          <div className={styles.progressBarTrack}>
                            <div
                              className={`${styles.progressBarFill} ${
                                stage === 'approved'
                                  ? styles.fillEmerald
                                  : stage === 'returned'
                                  ? styles.fillAmber
                                  : stage === 'rejected'
                                  ? styles.fillRose
                                  : styles.fillBlue
                              }`}
                              style={{
                                width: `${
                                  funnelReport.total_plans > 0
                                    ? Math.max(5, (count / funnelReport.total_plans) * 100)
                                    : 0
                                }%`,
                              }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 6: Graduation Risk */}
              {activeTab === 'risk' && riskReport && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                  <div className={styles.conversionGrid}>
                    <div className={styles.conversionCard}>
                      <div className={styles.conversionRate} style={{ color: '#ef4444' }}>
                        {riskReport.risk_levels.critical}
                      </div>
                      <div className={styles.conversionLabel}>Critical Risk Students</div>
                    </div>
                    <div className={styles.conversionCard}>
                      <div className={styles.conversionRate} style={{ color: '#f97316' }}>
                        {riskReport.risk_levels.high}
                      </div>
                      <div className={styles.conversionLabel}>High Risk Students</div>
                    </div>
                    <div className={styles.conversionCard}>
                      <div className={styles.conversionRate} style={{ color: '#eab308' }}>
                        {riskReport.risk_levels.medium}
                      </div>
                      <div className={styles.conversionLabel}>Medium Risk Students</div>
                    </div>
                    <div className={styles.conversionCard}>
                      <div className={styles.conversionRate} style={{ color: '#10b981' }}>
                        {riskReport.risk_levels.low + riskReport.risk_levels.none}
                      </div>
                      <div className={styles.conversionLabel}>Low / No Risk Students</div>
                    </div>
                  </div>

                  <Table
                    columns={riskColumns}
                    data={riskReport.programme_breakdown}
                    keyExtractor={(item) => item.programme_id}
                    caption="Academic Risk Distribution by Programme"
                    emptyState={<EmptyState title="No students assessed for risk" />}
                  />
                </div>
              )}

              {/* Tab 7: Elective Demand */}
              {activeTab === 'demand' && demandReport && (
                <div>
                  <Table
                    columns={demandColumns}
                    data={demandReport.items}
                    keyExtractor={(item) => `${item.course_id}-${item.term_code}`}
                    caption="Planned Elective Course Demand vs Scheduled Capacity"
                    emptyState={<EmptyState title="No elective course projections found" />}
                  />
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};
