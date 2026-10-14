import React, { useState } from 'react';
import { AcademicTerm } from '../../api/academicRecords';
import { Course } from '../../api/curriculum';
import styles from './CourseCatalogDrawer.module.css';

export interface CourseCatalogDrawerProps {
  courses: Course[];
  plannedCourseCodes: Set<string>;
  terms: AcademicTerm[];
  onAddCourse: (courseId: string, termId: string, termIndex: number) => void;
  isReadOnly?: boolean;
}

export const CourseCatalogDrawer: React.FC<CourseCatalogDrawerProps> = ({
  courses,
  plannedCourseCodes,
  terms,
  onAddCourse,
  isReadOnly = false,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTermByCourse, setSelectedTermByCourse] = useState<Record<string, string>>({});

  const filteredCourses = courses.filter((c) => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) return true;
    return (
      c.code.toLowerCase().includes(q) ||
      c.title.toLowerCase().includes(q)
    );
  });

  const handleSelectTerm = (courseId: string, termId: string) => {
    setSelectedTermByCourse((prev) => ({ ...prev, [courseId]: termId }));
  };

  const handleQuickAdd = (courseId: string) => {
    const termId = selectedTermByCourse[courseId] || (terms.length > 0 ? terms[0].id : '');
    if (!termId) return;
    const termIdx = terms.findIndex((t) => t.id === termId) + 1;
    onAddCourse(courseId, termId, termIdx);
  };

  return (
    <aside className={styles.drawerContainer} data-testid="course-catalog-drawer">
      <header className={styles.drawerHeader}>
        <div className={styles.titleRow}>
          <h2 className={styles.drawerTitle}>Curriculum Courses</h2>
          <span className={styles.courseCountBadge} data-testid="catalog-count-badge">
            {courses.length} courses
          </span>
        </div>
        <input
          type="search"
          className={styles.searchBar}
          placeholder="Filter courses by code or title..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          aria-label="Filter courses"
          data-testid="catalog-search-input"
        />
      </header>

      <div className={styles.courseList}>
        {filteredCourses.length === 0 ? (
          <div className={styles.emptySearch}>
            No curriculum courses match "{searchQuery}"
          </div>
        ) : (
          filteredCourses.map((c) => {
            const isPlanned = plannedCourseCodes.has(c.code);
            const currentSelectedTerm = selectedTermByCourse[c.id] || (terms[0]?.id ?? '');

            return (
              <div
                key={c.id}
                className={`${styles.catalogCard} ${isPlanned ? styles.alreadyPlanned : ''}`}
                draggable={!isReadOnly}
                onDragStart={(e) => {
                  e.dataTransfer.setData(
                    'application/json',
                    JSON.stringify({
                      courseId: c.id,
                      courseCode: c.code,
                    })
                  );
                }}
                data-testid={`catalog-card-${c.code}`}
              >
                <div className={styles.cardTop}>
                  <span className={styles.courseCode}>{c.code}</span>
                  <span className={styles.credits}>{Number(c.credits).toFixed(1)} cr</span>
                </div>
                <p className={styles.courseTitle} title={c.title}>
                  {c.title}
                </p>

                <div className={styles.cardFooter}>
                  <div className={styles.statusIndicator}>
                    {isPlanned ? (
                      <span className={styles.plannedBadge}>Planned</span>
                    ) : (
                      <span style={{ color: 'var(--color-slate-500)', fontSize: '0.72rem' }}>
                        Not planned
                      </span>
                    )}
                  </div>

                  {!isReadOnly && terms.length > 0 && (
                    <div className={styles.quickAddRow}>
                      <select
                        className={styles.termSelect}
                        aria-label={`Select term for ${c.code}`}
                        value={currentSelectedTerm}
                        onChange={(e) => handleSelectTerm(c.id, e.target.value)}
                        data-testid={`select-term-${c.code}`}
                      >
                        {terms.map((t, idx) => (
                          <option key={t.id} value={t.id}>
                            T{idx + 1}: {t.code}
                          </option>
                        ))}
                      </select>

                      <button
                        type="button"
                        className={styles.addBtn}
                        onClick={() => handleQuickAdd(c.id)}
                        aria-label={`Add ${c.code} to planned term`}
                        data-testid={`add-btn-${c.code}`}
                      >
                        + Add
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
};
