import React, { useState, useEffect, useCallback } from 'react';
import {
  advisingApi,
  ReviewQueueItem,
  PlanAuditLog,
  OverrideType,
} from '../api/advising';
import {
  planningApi,
  Plan,
  PlanVersion,
  PlanDiffReport,
} from '../api/planning';
import { ReviewQueueTable } from '../components/advising/ReviewQueueTable';
import { ReviewActionBar } from '../components/advising/ReviewActionBar';
import {
  ReviewDecisionDialog,
  DecisionSubmitData,
} from '../components/advising/ReviewDecisionDialog';
import { OverrideModal } from '../components/advising/OverrideModal';
import { ReviewAuditTimeline } from '../components/advising/ReviewAuditTimeline';
import { Badge } from '../components/Badge/Badge';
import styles from './AdvisorWorkspacePage.module.css';

export const AdvisorWorkspacePage: React.FC = () => {
  const [queue, setQueue] = useState<ReviewQueueItem[]>([]);
  const [isQueueLoading, setIsQueueLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  // Selected plan state
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);
  const [currentPlan, setCurrentPlan] = useState<Plan | null>(null);
  const [planVersions, setPlanVersions] = useState<PlanVersion[]>([]);
  const [auditLogs, setAuditLogs] = useState<PlanAuditLog[]>([]);
  const [isDetailLoading, setIsDetailLoading] = useState(false);

  // Active detail tab
  const [activeTab, setActiveTab] = useState<'simulation' | 'diff' | 'audit'>('simulation');

  // Modals & Action bar state
  const [decisionModalAction, setDecisionModalAction] = useState<
    'APPROVE' | 'RETURN' | 'REJECT' | null
  >(null);
  const [isOverrideModalOpen, setIsOverrideModalOpen] = useState(false);
  const [isActionSubmitting, setIsActionSubmitting] = useState(false);
  const [conflictError, setConflictError] = useState<string | null>(null);

  // Version diff state
  const [diffVersionA, setDiffVersionA] = useState<number>(1);
  const [diffVersionB, setDiffVersionB] = useState<number>(2);
  const [diffReport, setDiffReport] = useState<PlanDiffReport | null>(null);
  const [isDiffLoading, setIsDiffLoading] = useState(false);

  // 1. Load review queue
  const loadQueue = useCallback(async () => {
    setIsQueueLoading(true);
    try {
      const data = await advisingApi.fetchQueue({
        status: statusFilter !== 'ALL' ? statusFilter : undefined,
      });
      setQueue(data);
      if (data.length > 0) {
        setSelectedPlanId((prev) => prev || data[0].plan_id);
      }
    } catch (err) {
      console.error('Failed to fetch advisor review queue:', err);
    } finally {
      setIsQueueLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  // 2. Load selected plan details
  const loadPlanDetails = useCallback(async (planId: string) => {
    setIsDetailLoading(true);
    setConflictError(null);
    try {
      const [planData, versionsData, logsData] = await Promise.all([
        planningApi.fetchPlan(planId),
        planningApi.fetchPlanVersions(planId),
        advisingApi.fetchAuditHistory(planId),
      ]);
      setCurrentPlan(planData);
      setPlanVersions(versionsData);
      setAuditLogs(logsData);

      if (versionsData.length >= 2) {
        setDiffVersionA(versionsData[1].version_number);
        setDiffVersionB(versionsData[0].version_number);
      }
    } catch (err) {
      console.error('Failed to load plan details:', err);
    } finally {
      setIsDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedPlanId) {
      loadPlanDetails(selectedPlanId);
    } else {
      setCurrentPlan(null);
      setPlanVersions([]);
      setAuditLogs([]);
    }
  }, [selectedPlanId, loadPlanDetails]);

  // 3. Load diff report when diff tab active
  useEffect(() => {
    if (activeTab === 'diff' && selectedPlanId && planVersions.length >= 2) {
      setIsDiffLoading(true);
      planningApi
        .comparePlanVersions(selectedPlanId, diffVersionA, diffVersionB)
        .then((res) => setDiffReport(res))
        .catch((err) => console.error('Diff error:', err))
        .finally(() => setIsDiffLoading(false));
    }
  }, [activeTab, selectedPlanId, diffVersionA, diffVersionB, planVersions.length]);

  // Actions
  const handleStartReview = async () => {
    if (!currentPlan) return;
    setIsActionSubmitting(true);
    setConflictError(null);
    try {
      await advisingApi.startReview(currentPlan.id, {
        expected_row_version: currentPlan.row_version,
      });
      await loadPlanDetails(currentPlan.id);
      await loadQueue();
    } catch (err: unknown) {
      const res = (err as { response?: { status?: number; data?: { message?: string } } })?.response;
      if (res?.status === 409) {
        setConflictError(
          res.data?.message ||
            'Concurrent modification conflict. The degree plan was altered by another advisor or student.'
        );
      }
    } finally {
      setIsActionSubmitting(false);
    }
  };

  const handleDecisionConfirm = async (data: DecisionSubmitData) => {
    if (!currentPlan || !decisionModalAction) return;
    setIsActionSubmitting(true);
    setConflictError(null);
    try {
      if (decisionModalAction === 'APPROVE') {
        await advisingApi.approvePlan(currentPlan.id, {
          comments: data.comments,
          expected_row_version: currentPlan.row_version,
          idempotency_key: data.idempotency_key,
        });
      } else if (decisionModalAction === 'RETURN') {
        await advisingApi.returnPlan(currentPlan.id, {
          comments: data.comments,
          expected_row_version: currentPlan.row_version,
          idempotency_key: data.idempotency_key,
        });
      } else if (decisionModalAction === 'REJECT') {
        await advisingApi.rejectPlan(currentPlan.id, {
          comments: data.comments,
          expected_row_version: currentPlan.row_version,
          idempotency_key: data.idempotency_key,
        });
      }
      setDecisionModalAction(null);
      await loadPlanDetails(currentPlan.id);
      await loadQueue();
    } catch (err: unknown) {
      const res = (err as { response?: { status?: number; data?: { message?: string } } })?.response;
      if (res?.status === 409) {
        setConflictError(
          res.data?.message ||
            'Concurrency conflict detected (409 Conflict). Reloading latest plan state.'
        );
      }
    } finally {
      setIsActionSubmitting(false);
    }
  };

  const handleOverrideConfirm = async (data: {
    override_type: OverrideType;
    justification: string;
  }) => {
    if (!currentPlan) return;
    setIsActionSubmitting(true);
    try {
      await advisingApi.recordOverride(currentPlan.id, {
        override_type: data.override_type,
        justification: data.justification,
      });
      setIsOverrideModalOpen(false);
      await loadPlanDetails(currentPlan.id);
      await loadQueue();
    } catch (err) {
      console.error('Failed to record override:', err);
    } finally {
      setIsActionSubmitting(false);
    }
  };

  // Metrics computation
  const pendingCount = queue.filter(
    (q) => q.status === 'SUBMITTED' || q.status === 'RESUBMITTED'
  ).length;
  const underReviewCount = queue.filter((q) => q.status === 'UNDER_REVIEW').length;
  const overridesTotal = queue.reduce((sum, item) => sum + item.override_count, 0);
  const avgWaitDays =
    queue.length > 0
      ? Math.round(queue.reduce((sum, item) => sum + item.waiting_days, 0) / queue.length)
      : 0;

  const latestVersion = planVersions.length > 0 ? planVersions[0] : null;
  const sim = latestVersion?.snapshot_data?.simulation;

  return (
    <div className={styles.pageContainer}>
      <div className={styles.pageHeader}>
        <div>
          <span className={styles.preTitle}>Official Advising Workflow</span>
          <h1 className={styles.title}>Advisor Workspace & Degree Plan Review</h1>
          <p className={styles.subtitle}>
            Manage assigned student degree plans, evaluate curriculum rules, issue review
            decisions, and author strictly immutable overrides.
          </p>
        </div>
      </div>

      {/* Top Metrics Row */}
      <div className={styles.metricsGrid}>
        <div className={styles.metricCard}>
          <span className={styles.metricValue}>{pendingCount}</span>
          <span className={styles.metricLabel}>Awaiting Review</span>
        </div>
        <div className={styles.metricCard}>
          <span className={styles.metricValue}>{underReviewCount}</span>
          <span className={styles.metricLabel}>Currently In Review</span>
        </div>
        <div className={styles.metricCard}>
          <span className={styles.metricValue}>{overridesTotal}</span>
          <span className={styles.metricLabel}>Overrides Recorded</span>
        </div>
        <div className={styles.metricCard}>
          <span className={styles.metricValue}>{avgWaitDays}d</span>
          <span className={styles.metricLabel}>Average Wait Time</span>
        </div>
      </div>

      {conflictError && (
        <div className={`${styles.alertBox} ${styles.alertHard}`}>
          <span className={styles.alertTitle}>Optimistic Concurrency Conflict (409)</span>
          <span>{conflictError}</span>
          <button
            style={{ alignSelf: 'flex-start', padding: '4px 10px', marginTop: '4px' }}
            onClick={() => currentPlan && loadPlanDetails(currentPlan.id)}
          >
            Reload Latest Version
          </button>
        </div>
      )}

      {/* Queue Table */}
      <ReviewQueueTable
        queue={queue}
        selectedPlanId={selectedPlanId}
        onSelectPlan={(id) => setSelectedPlanId(id)}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        searchQuery={searchQuery}
        onSearchQueryChange={setSearchQuery}
        isLoading={isQueueLoading}
      />

      {/* Plan Detailed Review Section */}
      {currentPlan && (
        <div className={styles.reviewSection}>
          <ReviewActionBar
            plan={currentPlan}
            latestVersion={latestVersion}
            onStartReview={handleStartReview}
            onOpenDecisionDialog={(act) => setDecisionModalAction(act)}
            onOpenOverrideModal={() => setIsOverrideModalOpen(true)}
            isActionLoading={isActionSubmitting || isDetailLoading}
          />

          <div className={styles.detailCard}>
            <div className={styles.tabNav}>
              <button
                className={`${styles.tabBtn} ${
                  activeTab === 'simulation' ? styles.tabBtnActive : ''
                }`}
                onClick={() => setActiveTab('simulation')}
              >
                Compliance & Schedule Simulation
              </button>
              <button
                className={`${styles.tabBtn} ${
                  activeTab === 'diff' ? styles.tabBtnActive : ''
                }`}
                onClick={() => setActiveTab('diff')}
              >
                Version Diff & Snapshots ({planVersions.length})
              </button>
              <button
                className={`${styles.tabBtn} ${
                  activeTab === 'audit' ? styles.tabBtnActive : ''
                }`}
                onClick={() => setActiveTab('audit')}
              >
                Audit Trail & History ({auditLogs.length})
              </button>
            </div>

            {/* TAB 1: Simulation */}
            {activeTab === 'simulation' && (
              <div className={styles.tabContent}>
                {sim ? (
                  <>
                    {/* Constraints Summary */}
                    {sim.hard_constraints && sim.hard_constraints.length > 0 && (
                      <div className={`${styles.alertBox} ${styles.alertHard}`}>
                        <span className={styles.alertTitle}>
                          Hard Prerequisite / Policy Violations ({sim.hard_constraints.length})
                        </span>
                        <ul>
                          {sim.hard_constraints.map((c, i) => (
                            <li key={i}>
                              <strong>{c.code}:</strong> {c.message}{' '}
                              {c.course_code && `[${c.course_code}]`}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {sim.warnings && sim.warnings.length > 0 && (
                      <div className={`${styles.alertBox} ${styles.alertWarning}`}>
                        <span className={styles.alertTitle}>
                          Advisory Policy Warnings ({sim.warnings.length})
                        </span>
                        <ul>
                          {sim.warnings.map((w, i) => (
                            <li key={i}>{w.message}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {(!sim.hard_constraints || sim.hard_constraints.length === 0) &&
                      (!sim.warnings || sim.warnings.length === 0) && (
                        <div className={`${styles.alertBox} ${styles.alertSuccess}`}>
                          <span className={styles.alertTitle}>Simulation Verified Clean</span>
                          <span>
                            This submitted plan snapshot strictly satisfies all prerequisite rules,
                            term credit bounds, and requirement group thresholds.
                          </span>
                        </div>
                      )}

                    {/* Planned Terms Course Grid */}
                    <div className={styles.termGrid}>
                      {sim.terms &&
                        sim.terms.map((t) => (
                          <div key={t.term_id} className={styles.termCard}>
                            <div className={styles.termHeader}>
                              <span>{t.term_name || t.term_code}</span>
                              <Badge variant="neutral">{t.total_credits} cr</Badge>
                            </div>
                            <div className={styles.courseList}>
                              {t.courses && t.courses.length > 0 ? (
                                t.courses.map((c) => (
                                  <div key={c.course_id} className={styles.courseItem}>
                                    <div>
                                      <strong>{c.course_code}</strong>
                                      <div style={{ color: 'var(--color-slate-500)' }}>
                                        {c.course_title}
                                      </div>
                                    </div>
                                    <span>{c.credits} cr</span>
                                  </div>
                                ))
                              ) : (
                                <span style={{ color: 'var(--color-slate-400)', fontSize: '12px' }}>
                                  No courses scheduled
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                    </div>
                  </>
                ) : (
                  <div>No frozen simulation snapshot available.</div>
                )}
              </div>
            )}

            {/* TAB 2: Version Diff */}
            {activeTab === 'diff' && (
              <div className={styles.tabContent}>
                {planVersions.length < 2 ? (
                  <div style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>
                    Only 1 version snapshot exists for this plan. A diff report requires at least 2
                    submitted revisions.
                  </div>
                ) : (
                  <div className={styles.diffSection}>
                    <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                      <span>Compare Version:</span>
                      <select
                        value={diffVersionA}
                        onChange={(e) => setDiffVersionA(Number(e.target.value))}
                        style={{ padding: '4px 8px', borderRadius: '4px' }}
                      >
                        {planVersions.map((v) => (
                          <option key={v.version_number} value={v.version_number}>
                            v{v.version_number} ({v.status})
                          </option>
                        ))}
                      </select>
                      <span>with:</span>
                      <select
                        value={diffVersionB}
                        onChange={(e) => setDiffVersionB(Number(e.target.value))}
                        style={{ padding: '4px 8px', borderRadius: '4px' }}
                      >
                        {planVersions.map((v) => (
                          <option key={v.version_number} value={v.version_number}>
                            v{v.version_number} ({v.status})
                          </option>
                        ))}
                      </select>
                    </div>

                    {isDiffLoading ? (
                      <div>Computing snapshot diff...</div>
                    ) : diffReport ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        <div>
                          <strong>Added Courses ({diffReport.items_added?.length || 0}):</strong>
                          <ul>
                            {diffReport.items_added?.map((item, idx) => (
                              <li key={idx} className={styles.diffAdded}>
                                + {item.course_code} ({item.course_title}) in {item.term_code}
                              </li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <strong>
                            Removed Courses ({diffReport.items_removed?.length || 0}):
                          </strong>
                          <ul>
                            {diffReport.items_removed?.map((item, idx) => (
                              <li key={idx} className={styles.diffRemoved}>
                                - {item.course_code} ({item.course_title}) from {item.term_code}
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    ) : null}
                  </div>
                )}
              </div>
            )}

            {/* TAB 3: Audit Trail */}
            {activeTab === 'audit' && (
              <div className={styles.tabContent}>
                <ReviewAuditTimeline logs={auditLogs} isLoading={isDetailLoading} />
              </div>
            )}
          </div>
        </div>
      )}

      {/* Decision Modal (Approve / Return / Reject) */}
      <ReviewDecisionDialog
        isOpen={Boolean(decisionModalAction)}
        action={decisionModalAction}
        planName={currentPlan?.name || ''}
        versionNumber={latestVersion?.version_number || 1}
        rowVersion={currentPlan?.row_version || 1}
        onClose={() => setDecisionModalAction(null)}
        onConfirm={handleDecisionConfirm}
        isLoading={isActionSubmitting}
      />

      {/* Override Modal */}
      <OverrideModal
        isOpen={isOverrideModalOpen}
        planName={currentPlan?.name || ''}
        versionNumber={latestVersion?.version_number || 1}
        onClose={() => setIsOverrideModalOpen(false)}
        onConfirm={handleOverrideConfirm}
        isLoading={isActionSubmitting}
      />
    </div>
  );
};
