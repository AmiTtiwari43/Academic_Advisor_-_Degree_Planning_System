import React from 'react';
import { AcademicTerm } from '../../api/academicRecords';
import {
  PlanItem,
  PlanSimulationReport,
} from '../../api/planning';
import { SemesterColumn } from './SemesterColumn';
import styles from './SemesterColumnGrid.module.css';

export interface SemesterColumnGridProps {
  terms: AcademicTerm[];
  items: PlanItem[];
  simulationReport?: PlanSimulationReport | null;
  onRemoveCourse: (itemId: string) => void;
  onMoveCourse: (itemId: string, targetTermId: string, targetTermIndex: number) => void;
  onDropCourse: (payload: { itemId?: string; courseId?: string; fromTermId?: string }, targetTermId: string, targetTermIndex: number) => void;
  isReadOnly?: boolean;
}

export const SemesterColumnGrid: React.FC<SemesterColumnGridProps> = ({
  terms,
  items = [],
  simulationReport,
  onRemoveCourse,
  onMoveCourse,
  onDropCourse,
  isReadOnly = false,
}) => {
  const safeItems = Array.isArray(items) ? items : [];

  return (
    <div className={styles.gridContainer} data-testid="semester-column-grid">
      <div className={styles.gridActions}>
        <span className={styles.termCount}>
          Displaying {terms.length} Planned Semester{terms.length === 1 ? '' : 's'}
        </span>
      </div>

      <div className={styles.columnsWrapper}>
        {terms.map((term, idx) => {
          const termIndex = idx + 1;
          const termItems = safeItems.filter(
            (it) => it.planned_term === term.id || it.term_index === termIndex
          );

          const termStatus = simulationReport?.terms.find(
            (t) => t.term_id === term.id || t.term_index === termIndex
          );

          return (
            <SemesterColumn
              key={term.id}
              term={term}
              termIndex={termIndex}
              items={termItems}
              termStatus={termStatus}
              allTerms={terms}
              onRemoveCourse={onRemoveCourse}
              onMoveCourse={onMoveCourse}
              onDropCourse={onDropCourse}
              isReadOnly={isReadOnly}
            />
          );
        })}
      </div>
    </div>
  );
};
