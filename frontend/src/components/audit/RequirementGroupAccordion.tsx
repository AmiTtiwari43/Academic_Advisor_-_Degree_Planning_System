import React, { useState } from 'react';
import { RequirementGroupAudit } from '../../api/academicRecords';
import styles from './RequirementGroupAccordion.module.css';

interface RequirementGroupAccordionProps {
  group: RequirementGroupAudit;
  onCheckEligibility: (courseId: string, courseCode: string, courseTitle: string) => void;
  defaultExpanded?: boolean;
}

export const RequirementGroupAccordion: React.FC<RequirementGroupAccordionProps> = ({
  group,
  onCheckEligibility,
  defaultExpanded = true,
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const getGroupTypeBadgeClass = (type: string) => {
    switch (type) {
      case 'MANDATORY':
        return styles.badgeMandatory;
      case 'ELECTIVE':
        return styles.badgeElective;
      case 'CREDIT_CATEGORY':
        return styles.badgeCategory;
      default:
        return styles.badgeDefault;
    }
  };

  const getSourceBadgeClass = (source: string) => {
    switch (source) {
      case 'TRANSFER':
        return styles.badgeTransfer;
      case 'EXEMPTION':
        return styles.badgeExemption;
      default:
        return styles.badgeTranscript;
    }
  };

  return (
    <div
      className={`${styles.accordionCard} ${group.is_satisfied ? styles.cardSatisfied : styles.cardPending}`}
      data-testid={`requirement-group-${group.group_id}`}
    >
      <header
        className={styles.header}
        onClick={() => setIsExpanded(!isExpanded)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setIsExpanded(!isExpanded);
          }
        }}
        tabIndex={0}
        role="button"
        aria-expanded={isExpanded}
        aria-controls={`group-content-${group.group_id}`}
      >
        <div className={styles.headerLeft}>
          <span className={styles.expandIcon} aria-hidden="true">
            {isExpanded ? '▼' : '▶'}
          </span>
          <div className={styles.titleWrapper}>
            <h3 className={styles.groupTitle}>{group.name}</h3>
            <span className={`${styles.typeBadge} ${getGroupTypeBadgeClass(group.group_type)}`}>
              {group.group_type}
            </span>
          </div>
        </div>

        <div className={styles.headerRight}>
          <div className={styles.creditsSummary}>
            <span className={styles.creditsEarned} data-testid={`group-earned-${group.group_id}`}>
              {group.earned_credits}
            </span>
            <span className={styles.creditsRequired}>/ {group.min_credits} cr</span>
            {group.in_progress_credits > 0 && (
              <span className={styles.inProgressPill} title="In Progress (not yet earned)">
                +{group.in_progress_credits} in prog
              </span>
            )}
          </div>

          <span
            className={`${styles.statusBadge} ${group.is_satisfied ? styles.statusBadgeSatisfied : styles.statusBadgeUnsatisfied}`}
            data-testid={`group-status-${group.group_id}`}
          >
            {group.is_satisfied ? 'Satisfied' : `${group.remaining_credits} cr needed`}
          </span>
        </div>
      </header>

      {isExpanded && (
        <div id={`group-content-${group.group_id}`} className={styles.body}>
          {/* Allocated Courses Section */}
          <div className={styles.sectionBlock}>
            <div className={styles.sectionHeader}>
              <h4 className={styles.sectionSubtitle}>Allocated Completed Courses</h4>
              <span className={styles.sectionCount}>
                {group.allocated_courses.length} {group.allocated_courses.length === 1 ? 'course' : 'courses'}
              </span>
            </div>

            {group.allocated_courses.length === 0 ? (
              <div className={styles.emptyCoursesNotice}>
                No completed courses allocated to this group yet.
              </div>
            ) : (
              <div className={styles.tableResponsive}>
                <table className={styles.coursesTable}>
                  <thead>
                    <tr>
                      <th>Course Code</th>
                      <th>Title</th>
                      <th>Credits</th>
                      <th>Grade</th>
                      <th>Source</th>
                      <th>Attempt</th>
                    </tr>
                  </thead>
                  <tbody>
                    {group.allocated_courses.map((c, idx) => (
                      <tr key={c.course_id ? `${c.course_id}-${idx}` : `${c.course_code || 'course'}-${idx}`}>
                        <td className={styles.codeCell}>{c.course_code}</td>
                        <td className={styles.titleCell}>{c.course_title || (c as unknown as { title?: string }).title}</td>
                        <td className={styles.creditsCell}>{c.earned_credits}</td>
                        <td className={styles.gradeCell}>
                          <span className={styles.gradeBadge}>{c.grade || 'CR'}</span>
                        </td>
                        <td>
                          <span className={`${styles.sourceBadge} ${getSourceBadgeClass(c.source)}`}>
                            {c.source}
                          </span>
                        </td>
                        <td className={styles.attemptCell}>#{c.attempt_number ?? 1}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Remaining Mandatory Courses Section */}
          {group.remaining_mandatory_courses.length > 0 && (
            <div className={styles.sectionBlock}>
              <div className={styles.sectionHeader}>
                <h4 className={styles.sectionSubtitleWarning}>Required Mandatory Courses Remaining</h4>
                <span className={styles.sectionCountWarning}>
                  {group.remaining_mandatory_courses.length} unfulfilled
                </span>
              </div>
              <div className={styles.remainingList}>
                {group.remaining_mandatory_courses.map((rem, idx) => (
                  <div
                    key={rem.course_id || rem.course_code || `rem-${idx}`}
                    className={styles.remainingCard}
                    data-testid={`remaining-course-${rem.course_code}`}
                  >
                    <div className={styles.remainingDetails}>
                      <span className={styles.remainingCode}>{rem.course_code}</span>
                      <span className={styles.remainingTitle}>{rem.course_title || (rem as unknown as { title?: string }).title}</span>
                      <span className={styles.remainingCredits}>({rem.credits} cr)</span>
                    </div>
                    <button
                      type="button"
                      className={styles.checkEligibilityBtn}
                      onClick={(e) => {
                        e.stopPropagation();
                        onCheckEligibility(rem.course_id || rem.course_code, rem.course_code, rem.course_title || (rem as unknown as { title?: string }).title || rem.course_code);
                      }}
                      data-testid={`check-eligibility-btn-${rem.course_code}`}
                    >
                      Check Eligibility
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* In-Progress Courses Section */}
          {group.in_progress_courses.length > 0 && (
            <div className={styles.sectionBlock}>
              <div className={styles.sectionHeader}>
                <h4 className={styles.sectionSubtitleInfo}>Currently Enrolled (In Progress)</h4>
              </div>
              <div className={styles.inProgressList}>
                {group.in_progress_courses.map((ip, idx) => (
                  <div
                    key={ip.course_id || ip.course_code || `ip-${idx}`}
                    className={styles.inProgressCard}
                  >
                    <span className={styles.inProgressCode}>{ip.course_code}</span>
                    <span className={styles.inProgressTitle}>{ip.course_title || (ip as unknown as { title?: string }).title}</span>
                    <span className={styles.inProgressCredits}>({ip.credits} cr)</span>
                    <span className={styles.inProgressTag}>In Progress — Not Yet Earned</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
