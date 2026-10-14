import React, { useState } from 'react';
import { AcademicTerm } from '../../api/academicRecords';
import {
  PlanItem,
  PlanSimulationCourseStatus,
  PlanSimulationTermDetail,
} from '../../api/planning';
import styles from './SemesterColumn.module.css';

export interface SemesterColumnProps {
  term: AcademicTerm;
  termIndex: number;
  items: PlanItem[];
  termStatus?: PlanSimulationTermDetail;
  allTerms: AcademicTerm[];
  onRemoveCourse: (itemId: string) => void;
  onMoveCourse: (itemId: string, targetTermId: string, targetTermIndex: number) => void;
  onDropCourse: (payload: { itemId?: string; courseId?: string; fromTermId?: string }, targetTermId: string, targetTermIndex: number) => void;
  isReadOnly?: boolean;
}

export const SemesterColumn: React.FC<SemesterColumnProps> = ({
  term,
  termIndex,
  items,
  termStatus,
  allTerms,
  onRemoveCourse,
  onMoveCourse,
  onDropCourse,
  isReadOnly = false,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);

  const termCredits = items.reduce(
    (sum, it) => sum + Number(it.course_credits || 0),
    0
  );

  const isFallOrSpring = term.season === 'FALL' || term.season === 'SPRING';
  let loadBadgeClass = styles.statusNormal;
  let loadBadgeText = 'Optimal';

  if (termCredits > 21) {
    loadBadgeClass = styles.statusCeiling;
    loadBadgeText = 'Ceiling Exceeded';
  } else if (termCredits > 18) {
    loadBadgeClass = styles.statusOverload;
    loadBadgeText = 'Overload (18 max)';
  } else if (isFallOrSpring && termCredits > 0 && termCredits < 12) {
    loadBadgeClass = styles.statusUnderload;
    loadBadgeText = 'Underload (12 min)';
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!isReadOnly) {
      setIsDragOver(true);
    }
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (isReadOnly) return;

    try {
      const rawData = e.dataTransfer.getData('application/json');
      if (rawData) {
        const parsed = JSON.parse(rawData);
        onDropCourse(parsed, term.id, termIndex);
      }
    } catch {
      // ignore invalid drag payloads
    }
  };

  return (
    <div
      className={`${styles.columnContainer} ${isDragOver ? styles.dragOver : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      data-testid={`semester-column-${term.code}`}
    >
      <header className={styles.columnHeader}>
        <div className={styles.headerRow}>
          <h3 className={styles.termTitle}>{term.name || term.code}</h3>
          <span className={styles.termIndexBadge}>Term {termIndex}</span>
        </div>
        <div className={styles.creditLoadRow}>
          <span className={styles.creditTotal}>{termCredits.toFixed(1)} Credits</span>
          {termCredits > 0 && (
            <span
              className={`${styles.creditStatusBadge} ${loadBadgeClass}`}
              data-testid={`term-${term.code}-status`}
            >
              {loadBadgeText}
            </span>
          )}
        </div>
      </header>

      <div className={styles.courseList}>
        {items.length === 0 ? (
          <div className={styles.emptyState}>
            <span>No courses scheduled</span>
            {!isReadOnly && <small>Drag course here or use "Move to Term"</small>}
          </div>
        ) : (
          items.map((it) => {
            const courseSim: PlanSimulationCourseStatus | undefined =
              termStatus?.courses.find(
                (c) => c.course_id === it.course || c.course_code === it.course_code
              );

            return (
              <div
                key={it.id}
                className={styles.courseCard}
                draggable={!isReadOnly}
                onDragStart={(e) => {
                  e.dataTransfer.setData(
                    'application/json',
                    JSON.stringify({
                      itemId: it.id,
                      courseId: it.course,
                      fromTermId: term.id,
                      fromTermIndex: termIndex,
                    })
                  );
                }}
                data-testid={`plan-item-${it.course_code}`}
              >
                <div className={styles.courseCardHeader}>
                  <span className={styles.courseCode}>{it.course_code}</span>
                  <span className={styles.courseCredits}>
                    {Number(it.course_credits).toFixed(1)} cr
                  </span>
                </div>
                <p className={styles.courseTitle} title={it.course_title}>
                  {it.course_title}
                </p>

                {/* Simulation eligibility indicator */}
                {courseSim && (
                  <div className={styles.courseEligibilityRow}>
                    {courseSim.is_eligible ? (
                      <span className={styles.eligibleBadge} title="Prerequisites satisfied">
                        ✓ Eligible
                      </span>
                    ) : (
                      <span
                        className={styles.ineligibleBadge}
                        title={courseSim.blocking_reasons.join(', ')}
                      >
                        ✕ Prerequisite issue
                      </span>
                    )}

                    {!courseSim.offering_available && (
                      <span className={styles.notOfferedBadge} title="Not scheduled for this term">
                        ⚠️ Not offered
                      </span>
                    )}
                  </div>
                )}

                {courseSim && !courseSim.is_eligible && courseSim.blocking_reasons.length > 0 && (
                  <ul className={styles.blockingReasonList}>
                    {courseSim.blocking_reasons.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                )}

                {/* Accessible Action Controls */}
                {!isReadOnly && (
                  <div className={styles.cardActionRow}>
                    <select
                      className={styles.moveSelect}
                      aria-label={`Move ${it.course_code} to another term`}
                      value=""
                      onChange={(e) => {
                        const targetTermId = e.target.value;
                        if (!targetTermId) return;
                        const targetTermObj = allTerms.find((t) => t.id === targetTermId);
                        const targetIndex = allTerms.findIndex((t) => t.id === targetTermId) + 1;
                        if (targetTermObj) {
                          onMoveCourse(it.id, targetTermId, targetIndex);
                        }
                      }}
                    >
                      <option value="">Move to...</option>
                      {allTerms
                        .filter((t) => t.id !== term.id)
                        .map((t, idx) => (
                          <option key={t.id} value={t.id}>
                            Term {idx + 1}: {t.code}
                          </option>
                        ))}
                    </select>

                    <button
                      type="button"
                      className={styles.removeButton}
                      aria-label={`Remove ${it.course_code} from ${term.name}`}
                      onClick={() => onRemoveCourse(it.id)}
                    >
                      Remove
                    </button>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
