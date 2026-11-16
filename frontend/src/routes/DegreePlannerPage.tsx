import React, { useEffect, useState, useCallback } from 'react';
import {
  AcademicTerm,
  StudentRecord,
  academicRecordsApi,
} from '../api/academicRecords';
import { Course, curriculumApi } from '../api/curriculum';
import {
  Plan,
  PlanSimulationReport,
  planningApi,
} from '../api/planning';
import { SemesterColumnGrid } from '../components/planning/SemesterColumnGrid';
import { CourseCatalogDrawer } from '../components/planning/CourseCatalogDrawer';
import { PlanSimulationPanel } from '../components/planning/PlanSimulationPanel';
import { PlanVersionDiffModal } from '../components/planning/PlanVersionDiffModal';
import { WhatIfModal } from '../components/planning/WhatIfModal';
import styles from './DegreePlannerPage.module.css';

export const DegreePlannerPage: React.FC = () => {
  const [studentRecords, setStudentRecords] = useState<StudentRecord[]>([]);
  const [selectedRecordId, setSelectedRecordId] = useState<string>('');
  const [plans, setPlans] = useState<Plan[]>([]);
  const [activePlan, setActivePlan] = useState<Plan | null>(null);
  const [academicTerms, setAcademicTerms] = useState<AcademicTerm[]>([]);
  const [catalogCourses, setCatalogCourses] = useState<Course[]>([]);
  const [simulation, setSimulation] = useState<PlanSimulationReport | null>(null);

  const [loading, setLoading] = useState(true);
  const [isSimulating, setIsSimulating] = useState(false);
  const [isMutating, setIsMutating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conflictError, setConflictError] = useState<string | null>(null);

  // Modal states
  const [diffModalOpen, setDiffModalOpen] = useState(false);
  const [whatIfModalOpen, setWhatIfModalOpen] = useState(false);
  const [submitDialogOpen, setSubmitDialogOpen] = useState(false);
  const [submissionNote, setSubmissionNote] = useState('');

  // 1. Initial Load: Student Records, Academic Terms, Courses
  useEffect(() => {
    let isMounted = true;
    Promise.all([
      academicRecordsApi.getStudentRecords(),
      academicRecordsApi.getAcademicTerms(),
      curriculumApi.getCourses(),
    ])
      .then(([records, terms, courses]) => {
        if (!isMounted) return;
        const recordsList = Array.isArray(records)
          ? records
          : (records as unknown as { results?: StudentRecord[] })?.results || [];
        const termsList = Array.isArray(terms)
          ? terms
          : (terms as unknown as { results?: AcademicTerm[] })?.results || [];
        const coursesList = Array.isArray(courses)
          ? courses
          : (courses as unknown as { results?: Course[] })?.results || [];

        setStudentRecords(recordsList);
        // Sort terms chronologically
        const sortedTerms = [...termsList].sort(
          (a, b) => new Date(a.start_date).getTime() - new Date(b.start_date).getTime()
        );
        setAcademicTerms(sortedTerms);
        setCatalogCourses(coursesList);

        if (recordsList.length > 0) {
          setSelectedRecordId(recordsList[0].id);
        } else {
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err.message || 'Failed to initialize degree planner.');
        setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // 2. Fetch Plans for selected student record
  const loadPlans = useCallback(
    (recordId: string, preferredPlanId?: string, isBackground = false) => {
      if (!recordId) return;
      if (!isBackground) {
        setLoading(true);
        setConflictError(null);
      }

      planningApi
        .fetchPlans(recordId)
        .then((data) => {
          const list = Array.isArray(data)
            ? data
            : (data as unknown as { results?: Plan[] })?.results || [];
          setPlans(list);
          if (list.length > 0) {
            const match = preferredPlanId
              ? list.find((p) => p.id === preferredPlanId) || list[0]
              : list.find((p) => p.is_primary) || list[0];
            return planningApi.fetchPlan(match.id);
          } else {
            setActivePlan(null);
            setSimulation(null);
            return null;
          }
        })
        .then((fullPlan) => {
          if (fullPlan) {
            setActivePlan(fullPlan);
          }
        })
        .catch((err) => {
          setError(err.message || 'Failed to fetch student degree plans.');
        })
        .finally(() => {
          if (!isBackground) {
            setLoading(false);
          }
        });
    },
    []
  );

  useEffect(() => {
    if (selectedRecordId) {
      loadPlans(selectedRecordId);
    }
  }, [selectedRecordId, loadPlans]);

  // 3. Run Simulation whenever activePlan changes
  const runSimulation = useCallback((planId: string) => {
    setIsSimulating(true);
    planningApi
      .simulatePlan(planId)
      .then((sim) => {
        setSimulation(sim);
      })
      .catch((err) => {
        console.error('Simulation error:', err);
      })
      .finally(() => {
        setIsSimulating(false);
      });
  }, []);

  useEffect(() => {
    if (activePlan) {
      runSimulation(activePlan.id);
    }
  }, [activePlan?.id, runSimulation]);

  // 4. Create Plan
  const handleCreatePlan = () => {
    if (!selectedRecordId) return;
    const planName = prompt('Enter a name for this degree plan:', '4-Year Academic Graduation Plan');
    if (!planName) return;

    setLoading(true);
    planningApi
      .createPlan({
        student_record: selectedRecordId,
        name: planName,
        is_primary: plans.length === 0,
      })
      .then((newPlan) => {
        loadPlans(selectedRecordId, newPlan.id);
      })
      .catch((err) => {
        setError(err.message || 'Failed to create degree plan.');
        setLoading(false);
      });
  };

  // 5. Add Course to Plan
  const handleAddCourse = (courseId: string, termId: string, termIndex: number) => {
    if (!activePlan || isMutating) return;

    setIsMutating(true);
    setError(null);
    setConflictError(null);

    planningApi
      .addCourseToPlan(activePlan.id, {
        course: courseId,
        planned_term: termId,
        term_index: termIndex,
      })
      .then(() => {
        // Refresh active plan
        return planningApi.fetchPlan(activePlan.id);
      })
      .then((refreshed) => {
        setActivePlan(refreshed);
        runSimulation(refreshed.id);
      })
      .catch((err) => {
        if (err.status === 409) {
          setConflictError('Conflict: This plan was modified in another session. Reloading latest plan...');
          loadPlans(selectedRecordId, activePlan.id, true);
        } else {
          setError(err.message || 'Failed to add course to plan.');
        }
      })
      .finally(() => {
        setIsMutating(false);
      });
  };

  // 6. Remove Course from Plan
  const handleRemoveCourse = (itemId: string) => {
    if (!activePlan || isMutating) return;

    setIsMutating(true);
    setError(null);
    setConflictError(null);

    planningApi
      .removeCourseFromPlan(activePlan.id, itemId)
      .then(() => {
        return planningApi.fetchPlan(activePlan.id);
      })
      .then((refreshed) => {
        setActivePlan(refreshed);
        runSimulation(refreshed.id);
      })
      .catch((err) => {
        if (err.status === 409) {
          setConflictError('Conflict: This plan was modified elsewhere. Reloading latest version...');
          loadPlans(selectedRecordId, activePlan.id, true);
        } else {
          setError(err.message || 'Failed to remove course from plan.');
        }
      })
      .finally(() => {
        setIsMutating(false);
      });
  };

  // 7. Move Course between terms
  const handleMoveCourse = (itemId: string, targetTermId: string, targetTermIndex: number) => {
    if (!activePlan || isMutating) return;

    setIsMutating(true);
    setError(null);
    setConflictError(null);

    planningApi
      .moveCourseInPlan(activePlan.id, itemId, {
        target_term: targetTermId,
        target_term_index: targetTermIndex,
      })
      .then(() => {
        return planningApi.fetchPlan(activePlan.id);
      })
      .then((refreshed) => {
        setActivePlan(refreshed);
        runSimulation(refreshed.id);
      })
      .catch((err) => {
        if (err.status === 409) {
          setConflictError('Conflict: This plan was modified elsewhere. Reloading latest version...');
          loadPlans(selectedRecordId, activePlan.id, true);
        } else {
          setError(err.message || 'Failed to move course in plan.');
        }
      })
      .finally(() => {
        setIsMutating(false);
      });
  };

  // 8. Handle Drop (supports moving existing item or adding new catalog course)
  const handleDropCourse = (
    payload: { itemId?: string; courseId?: string; fromTermId?: string },
    targetTermId: string,
    targetTermIndex: number
  ) => {
    if (payload.itemId) {
      handleMoveCourse(payload.itemId, targetTermId, targetTermIndex);
    } else if (payload.courseId) {
      handleAddCourse(payload.courseId, targetTermId, targetTermIndex);
    }
  };

  // 9. Submit Plan for Advisor Review
  const handleConfirmSubmit = () => {
    if (!activePlan) return;

    setLoading(true);
    planningApi
      .submitPlan(activePlan.id, submissionNote)
      .then(() => {
        setSubmitDialogOpen(false);
        setSubmissionNote('');
        return planningApi.fetchPlan(activePlan.id);
      })
      .then((refreshed) => {
        setActivePlan(refreshed);
        runSimulation(refreshed.id);
      })
      .catch((err) => {
        setError(err.message || 'Failed to submit plan snapshot.');
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const plannedCourseCodes = new Set(
    (activePlan?.items || []).map((it) => it.course_code)
  );

  return (
    <div className={styles.pageContainer} data-testid="degree-planner-page">
      {/* Page Header */}
      <header className={styles.pageHeader}>
        <div>
          <span className={styles.preTitle}>Multi-Semester Degree Planning</span>
          <h1 className={styles.title}>Academic Degree Planner</h1>
          <p className={styles.subtitle}>
            Simulate term schedules, verify prerequisite chains, and model what-if scenarios.
          </p>
        </div>

        <div className={styles.headerControls}>
          {studentRecords.length > 1 && (
            <select
              className={styles.selectInput}
              value={selectedRecordId}
              onChange={(e) => setSelectedRecordId(e.target.value)}
              aria-label="Select student record"
              data-testid="student-record-select"
            >
              {studentRecords.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.student_username} ({r.programme_code})
                </option>
              ))}
            </select>
          )}

          {plans.length > 0 && (
            <select
              className={styles.selectInput}
              value={activePlan?.id ?? ''}
              onChange={(e) => {
                const p = plans.find((pl) => pl.id === e.target.value);
                if (p) {
                  setLoading(true);
                  planningApi
                    .fetchPlan(p.id)
                    .then(setActivePlan)
                    .catch((err) => setError(err.message || 'Failed to fetch plan detail.'))
                    .finally(() => setLoading(false));
                }
              }}
              aria-label="Select active plan"
              data-testid="plan-select"
            >
              {plans.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} {p.is_primary ? '(Primary)' : ''}
                </option>
              ))}
            </select>
          )}

          {activePlan && (
            <span
              className={`${styles.planStatusBadge} ${
                activePlan.status === 'SUBMITTED' ? styles.statusSubmitted : styles.statusDraft
              }`}
              data-testid="plan-status-badge"
            >
              {activePlan.status}
            </span>
          )}

          <button
            type="button"
            className={styles.btnPrimary}
            onClick={handleCreatePlan}
            data-testid="create-plan-btn"
          >
            + New Plan
          </button>
        </div>
      </header>

      {/* Conflict / Error Banner */}
      {conflictError && (
        <div className={styles.conflictAlert} data-testid="concurrency-conflict-alert">
          <span>⚠️ {conflictError}</span>
        </div>
      )}

      {/* Advisor Feedback & Revision Banners */}
      {activePlan?.status === 'RETURNED' && (
        <div
          style={{
            background: 'rgba(245, 158, 11, 0.1)',
            border: '1px solid rgba(245, 158, 11, 0.3)',
            borderRadius: 'var(--radius-md)',
            padding: 'var(--space-3) var(--space-4)',
            color: '#b45309',
            fontSize: 'var(--font-size-sm)',
          }}
          data-testid="returned-revision-banner"
        >
          <span>
            <strong>Action Required:</strong> Your degree plan was returned by your academic advisor
            for revision. Please update your semester course loads and submit an updated plan.
          </span>
        </div>
      )}

      {activePlan?.status === 'APPROVED' && (
        <div
          style={{
            background: 'rgba(16, 185, 129, 0.1)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            borderRadius: 'var(--radius-md)',
            padding: 'var(--space-3) var(--space-4)',
            color: '#065f46',
            fontSize: 'var(--font-size-sm)',
          }}
          data-testid="approved-plan-banner"
        >
          <span>
            <strong>Official Approval:</strong> This academic plan has been reviewed and officially
            approved by your academic advisor.
          </span>
        </div>
      )}


      {error && (
        <div
          style={{
            background: 'var(--color-status-danger-bg)',
            color: 'var(--color-status-danger-text)',
            padding: 'var(--space-3) var(--space-4)',
            borderRadius: 'var(--radius-md)',
            fontSize: 'var(--font-size-sm)',
          }}
          data-testid="planner-error-banner"
        >
          {error}
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: 'var(--space-12)' }}>
          Loading degree planning workspace...
        </div>
      ) : !activePlan ? (
        <div
          style={{
            background: 'var(--color-surface-pure)',
            border: 'var(--border-subtle)',
            borderRadius: 'var(--radius-lg)',
            padding: 'var(--space-12)',
            textAlign: 'center',
          }}
          data-testid="empty-planner-state"
        >
          <h2 style={{ fontFamily: 'var(--font-family-serif)', marginBottom: 'var(--space-2)' }}>
            No Degree Plans Created Yet
          </h2>
          <p style={{ color: 'var(--color-slate-500)', marginBottom: 'var(--space-4)' }}>
            Create your first multi-semester degree plan to start modeling course schedules.
          </p>
          <button
            type="button"
            className={styles.btnPrimary}
            onClick={handleCreatePlan}
            data-testid="create-first-plan-btn"
          >
            Create Multi-Semester Plan
          </button>
        </div>
      ) : (
        <>
          {/* Simulation & Validation Banner */}
          <PlanSimulationPanel
            simulation={simulation}
            planStatus={activePlan.status}
            isSimulating={isSimulating}
            onSimulate={() => runSimulation(activePlan.id)}
            onSubmitPlan={() => setSubmitDialogOpen(true)}
            onOpenWhatIf={() => setWhatIfModalOpen(true)}
            onOpenVersions={() => setDiffModalOpen(true)}
            isReadOnly={activePlan.status === 'SUBMITTED'}
          />

          {/* Planner Two-Column Grid & Course Drawer */}
          <div className={styles.workspaceLayout}>
            <div className={styles.plannerGridSection}>
              <SemesterColumnGrid
                terms={academicTerms}
                items={activePlan.items || []}
                simulationReport={simulation}
                onRemoveCourse={handleRemoveCourse}
                onMoveCourse={handleMoveCourse}
                onDropCourse={handleDropCourse}
                isReadOnly={activePlan.status === 'SUBMITTED'}
              />
            </div>

            <CourseCatalogDrawer
              courses={catalogCourses}
              plannedCourseCodes={plannedCourseCodes}
              terms={academicTerms}
              onAddCourse={handleAddCourse}
              isReadOnly={activePlan.status === 'SUBMITTED'}
            />
          </div>
        </>
      )}

      {/* Snapshot Version History & Diff Modal */}
      {activePlan && (
        <PlanVersionDiffModal
          planId={activePlan.id}
          isOpen={diffModalOpen}
          onClose={() => setDiffModalOpen(false)}
        />
      )}

      {/* What-If Scenario Simulation Modal */}
      {selectedRecordId && (
        <WhatIfModal
          studentRecordId={selectedRecordId}
          planId={activePlan?.id}
          isOpen={whatIfModalOpen}
          onClose={() => setWhatIfModalOpen(false)}
        />
      )}

      {/* Submission Confirmation Dialog */}
      {submitDialogOpen && (
        <div
          className={styles.submitDialogBackdrop}
          role="dialog"
          aria-modal="true"
          aria-labelledby="submit-dialog-title"
          data-testid="submit-plan-dialog"
        >
          <div className={styles.submitDialogContent}>
            <h2
              id="submit-dialog-title"
              style={{
                fontFamily: 'var(--font-family-serif)',
                fontSize: 'var(--font-size-lg)',
                margin: 0,
              }}
            >
              Submit Plan for Advisor Review
            </h2>
            <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-slate-500)', margin: 0 }}>
              Freezes an immutable snapshot (PlanVersion) of your plan for formal faculty review.
            </p>

            <div>
              <label
                htmlFor="submission-note-input"
                style={{
                  display: 'block',
                  fontSize: 'var(--font-size-xs)',
                  fontWeight: 600,
                  marginBottom: 'var(--space-1)',
                }}
              >
                Advisor Submission Note (Optional):
              </label>
              <textarea
                id="submission-note-input"
                className={styles.textareaInput}
                placeholder="E.g. Requesting approval for senior capstone prerequisites..."
                value={submissionNote}
                onChange={(e) => setSubmissionNote(e.target.value)}
                data-testid="submission-note-input"
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-3)' }}>
              <button
                type="button"
                className={styles.btnPrimary}
                style={{ background: 'var(--color-surface-pure)', color: 'var(--color-slate-700)' }}
                onClick={() => setSubmitDialogOpen(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className={styles.btnPrimary}
                onClick={handleConfirmSubmit}
                data-testid="confirm-submit-plan-btn"
              >
                Confirm & Submit Snapshot
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
