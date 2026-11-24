import React, { useState, useEffect, useCallback } from 'react';
import {
  Compass,
  Award,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  BookOpen,
  RefreshCw,
  Plus,
  Info,
  Check,
  GraduationCap,
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
import { Dialog } from '../components/Dialog/Dialog';
import { Input } from '../components/Input/Input';
import { Select } from '../components/Select/Select';
import {
  careerApi,
  CareerObjective,
  SkillGapReport,
  CourseRecommendation,
  Skill,
  CourseSkillMapping,
  SkillCategory,
} from '../api/career';
import { academicRecordsApi, StudentRecord } from '../api/academicRecords';
import styles from './CareerGuidancePage.module.css';

const TABS: TabItem[] = [
  { id: 'gap', label: 'Skill Gap Analysis' },
  { id: 'recommendations', label: 'Course Recommendations' },
  { id: 'taxonomy', label: 'Skills & Course Mappings' },
];

export const CareerGuidancePage: React.FC = () => {
  const { hasRole } = useAuth();
  const canManage = hasRole(['COORDINATOR', 'HOD', 'ADMIN']);

  const [activeTab, setActiveTab] = useState<string>('gap');

  // Objectives and selected objective
  const [objectives, setObjectives] = useState<CareerObjective[]>([]);
  const [selectedObjectiveId, setSelectedObjectiveId] = useState<string>('');
  const [isObjectivesLoading, setIsObjectivesLoading] = useState<boolean>(true);

  // Student Records State (for advisors, coordinators, and students)
  const [studentRecords, setStudentRecords] = useState<StudentRecord[]>([]);
  const [selectedRecordId, setSelectedRecordId] = useState<string>('');

  // Skill Gap State
  const [skillGapReport, setSkillGapReport] = useState<SkillGapReport | null>(null);
  const [isGapLoading, setIsGapLoading] = useState<boolean>(false);
  const [gapError, setGapError] = useState<string | null>(null);

  // Course Recommendations State
  const [recommendations, setRecommendations] = useState<CourseRecommendation[]>([]);
  const [isRecsLoading, setIsRecsLoading] = useState<boolean>(false);
  const [recsError, setRecsError] = useState<string | null>(null);

  // Taxonomy & Mappings State
  const [skills, setSkills] = useState<Skill[]>([]);
  const [courseMappings, setCourseMappings] = useState<CourseSkillMapping[]>([]);
  const [skillCategoryFilter, setSkillCategoryFilter] = useState<string>('ALL');
  const [skillSearchQuery, setSkillSearchQuery] = useState<string>('');
  const [isTaxonomyLoading, setIsTaxonomyLoading] = useState<boolean>(false);

  // Add Skill Modal State
  const [isAddSkillOpen, setIsAddSkillOpen] = useState<boolean>(false);
  const [newSkillCode, setNewSkillCode] = useState<string>('');
  const [newSkillName, setNewSkillName] = useState<string>('');
  const [newSkillCategory, setNewSkillCategory] = useState<SkillCategory>('TECHNICAL');
  const [newSkillDescription, setNewSkillDescription] = useState<string>('');
  const [isSubmittingSkill, setIsSubmittingSkill] = useState<boolean>(false);

  // Fetch Student Records
  useEffect(() => {
    let isMounted = true;
    academicRecordsApi
      .getStudentRecords()
      .then((records) => {
        if (!isMounted) return;
        const list = Array.isArray(records)
          ? records
          : (records as unknown as { results?: StudentRecord[] })?.results || [];
        setStudentRecords(list);
        if (list.length > 0) {
          setSelectedRecordId((prev) => prev || list[0].id);
        }
      })
      .catch(() => {
        // Fallback gracefully in testing environments or when unauthorized
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // 1. Load Career Objectives
  const loadObjectives = useCallback(async () => {
    setIsObjectivesLoading(true);
    try {
      const data = await careerApi.getObjectives({ is_active: true });
      const list = Array.isArray(data)
        ? data
        : (data as unknown as { results?: CareerObjective[] })?.results || [];
      setObjectives(list);
      if (list.length > 0 && !selectedObjectiveId) {
        setSelectedObjectiveId(list[0].id);
      }
    } catch {
      // Non-fatal, handle error in views
    } finally {
      setIsObjectivesLoading(false);
    }
  }, [selectedObjectiveId]);

  // 2. Load Skill Gap
  const loadSkillGap = useCallback(async () => {
    if (!selectedObjectiveId) return;
    setIsGapLoading(true);
    setGapError(null);
    try {
      const params: { objective_id: string; student_id?: string } = {
        objective_id: selectedObjectiveId,
      };
      if (selectedRecordId) {
        params.student_id = selectedRecordId;
      }
      const res = await careerApi.getSkillGap(params);
      setSkillGapReport(res);
    } catch {
      setGapError('Failed to load skill-gap analysis for selected career objective.');
    } finally {
      setIsGapLoading(false);
    }
  }, [selectedObjectiveId, selectedRecordId]);

  // 3. Load Recommendations
  const loadRecommendations = useCallback(async () => {
    if (!selectedObjectiveId) return;
    setIsRecsLoading(true);
    setRecsError(null);
    try {
      const params: { objective_id: string; limit: number; student_id?: string } = {
        objective_id: selectedObjectiveId,
        limit: 15,
      };
      if (selectedRecordId) {
        params.student_id = selectedRecordId;
      }
      const res = await careerApi.getRecommendations(params);
      const list = Array.isArray(res)
        ? res
        : (res as unknown as { results?: CourseRecommendation[] })?.results || [];
      setRecommendations(list);
    } catch {
      setRecsError('Failed to load course recommendations.');
    } finally {
      setIsRecsLoading(false);
    }
  }, [selectedObjectiveId, selectedRecordId]);

  // 4. Load Taxonomy
  const loadTaxonomy = useCallback(async () => {
    setIsTaxonomyLoading(true);
    try {
      const [skillsData, mappingsData] = await Promise.all([
        careerApi.getSkills(),
        careerApi.getCourseSkills(),
      ]);
      const skillsList = Array.isArray(skillsData)
        ? skillsData
        : (skillsData as unknown as { results?: Skill[] })?.results || [];
      const mappingsList = Array.isArray(mappingsData)
        ? mappingsData
        : (mappingsData as unknown as { results?: CourseSkillMapping[] })?.results || [];
      setSkills(skillsList);
      setCourseMappings(mappingsList);
    } catch {
      // Non-fatal
    } finally {
      setIsTaxonomyLoading(false);
    }
  }, []);

  useEffect(() => {
    loadObjectives();
  }, [loadObjectives]);

  useEffect(() => {
    if (studentRecords.length > 0 && !selectedRecordId) {
      return;
    }
    if (activeTab === 'gap') {
      loadSkillGap();
    } else if (activeTab === 'recommendations') {
      loadRecommendations();
    } else if (activeTab === 'taxonomy') {
      loadTaxonomy();
    }
  }, [activeTab, selectedObjectiveId, selectedRecordId, studentRecords.length, loadSkillGap, loadRecommendations, loadTaxonomy]);

  // Handle Set as Primary Preference
  const handleSetPrimary = async () => {
    if (!selectedObjectiveId) return;
    try {
      const payload: {
        career_objective: string;
        priority: number;
        notes: string;
        student_record?: string;
      } = {
        career_objective: selectedObjectiveId,
        priority: 1,
        notes: 'Set from Career Guidance workspace',
      };
      if (selectedRecordId) {
        payload.student_record = selectedRecordId;
      }
      await careerApi.createPreference(payload);
      loadSkillGap();
    } catch {
      // Handled silently or via toast
    }
  };

  // Handle Create Skill
  const handleCreateSkillSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSkillCode || !newSkillName) return;
    setIsSubmittingSkill(true);
    try {
      await careerApi.createSkill({
        code: newSkillCode.trim().toUpperCase(),
        name: newSkillName.trim(),
        category: newSkillCategory,
        description: newSkillDescription.trim(),
      });
      setIsAddSkillOpen(false);
      setNewSkillCode('');
      setNewSkillName('');
      setNewSkillDescription('');
      loadTaxonomy();
    } catch {
      // Handled in dialog
    } finally {
      setIsSubmittingSkill(false);
    }
  };

  // Table Columns for Taxonomy Skills
  const filteredSkills = skills.filter((s) => {
    const matchesCat = skillCategoryFilter === 'ALL' || s.category === skillCategoryFilter;
    const matchesSearch =
      !skillSearchQuery ||
      s.code.toLowerCase().includes(skillSearchQuery.toLowerCase()) ||
      s.name.toLowerCase().includes(skillSearchQuery.toLowerCase());
    return matchesCat && matchesSearch;
  });

  const skillColumns: Column<Skill>[] = [
    { key: 'code', header: 'Skill Code', sortable: true },
    { key: 'name', header: 'Skill Name', sortable: true },
    {
      key: 'category',
      header: 'Category',
      sortable: true,
      render: (s) => (
        <Badge variant={s.category === 'TECHNICAL' ? 'teal' : 'neutral'}>
          {s.category.replace('_', ' ')}
        </Badge>
      ),
    },
    { key: 'description', header: 'Description' },
  ];

  const mappingColumns: Column<CourseSkillMapping>[] = [
    { key: 'course_code', header: 'Course Code', sortable: true },
    { key: 'course_title', header: 'Course Title' },
    { key: 'skill_code', header: 'Skill Code', sortable: true },
    { key: 'skill_name', header: 'Skill Name' },
    {
      key: 'proficiency_level',
      header: 'Proficiency Level',
      sortable: true,
      render: (m) => <Badge variant="info">{m.proficiency_level}</Badge>,
    },
    {
      key: 'coverage_weight',
      header: 'Weight',
      align: 'right',
      render: (m) => `${(m.coverage_weight * 100).toFixed(0)}%`,
    },
  ];

  return (
    <div className={styles.pageContainer}>
      <PageHeader
        title="Career & Skill Guidance"
        subtitle="Align degree progression with industry skills, targeted career competencies, and explainable course recommendations."
        badge={<Badge variant="teal">Advisory Guidance Engine</Badge>}
        actions={
          <Button
            variant="outline"
            size="sm"
            leftIcon={<RefreshCw size={14} />}
            onClick={() => {
              if (activeTab === 'gap') loadSkillGap();
              else if (activeTab === 'recommendations') loadRecommendations();
              else if (activeTab === 'taxonomy') loadTaxonomy();
            }}
          >
            Refresh Guidance
          </Button>
        }
      />

      {/* Prominent Advisory Notice */}
      <div className={styles.advisoryBanner} role="note">
        <Info size={20} className={styles.advisoryIcon} />
        <div>
          <strong>Advisory Notice:</strong> Career skill recommendations and readiness scores are
          designed for academic planning guidance only. They do not replace formal degree completion
          requirements or institutional graduation certifications.
        </div>
      </div>

      {/* Target Career Objective Selector Bar */}
      <div className={styles.selectorBar}>
        {studentRecords.length > 0 && (
          <div className={styles.selectorGroup}>
            <label htmlFor="student-select" className={styles.selectorLabel}>
              Student:
            </label>
            <select
              id="student-select"
              className={styles.selectInput}
              value={selectedRecordId}
              onChange={(e) => setSelectedRecordId(e.target.value)}
              data-testid="student-record-select"
            >
              {studentRecords.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.student_preferred_name ||
                    (r.student_first_name
                      ? `${r.student_first_name} ${r.student_last_name}`
                      : r.student_username)}{' '}
                  [{r.student_registration_number || `STU-2026-${r.id}`}] ({r.programme_code})
                </option>
              ))}
            </select>
          </div>
        )}

        <div className={styles.selectorGroup}>
          <label htmlFor="objective-select" className={styles.selectorLabel}>
            Target Career Objective:
          </label>
          {isObjectivesLoading ? (
            <Skeleton width="260px" height="38px" />
          ) : (
            <select
              id="objective-select"
              className={styles.selectInput}
              value={selectedObjectiveId}
              onChange={(e) => setSelectedObjectiveId(e.target.value)}
            >
              {objectives.map((obj) => (
                <option key={obj.id} value={obj.id}>
                  {obj.title} ({obj.code})
                </option>
              ))}
            </select>
          )}
        </div>

        <div className={styles.selectorGroup}>
          <Button
            size="sm"
            variant="secondary"
            leftIcon={<Check size={14} />}
            onClick={handleSetPrimary}
          >
            Set as Primary Objective
          </Button>
        </div>
      </div>

      {/* Main Workspace Card */}
      <div className={styles.workspaceCard}>
        <Tabs tabs={TABS} activeTab={activeTab} onChange={(id) => setActiveTab(id)} />

        <div className={styles.workspaceContent}>
          {/* TAB 1: SKILL GAP ANALYSIS */}
          {activeTab === 'gap' && (
            <>
              {isGapLoading ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  <Skeleton height="100px" />
                  <Skeleton height="200px" />
                </div>
              ) : gapError ? (
                <ErrorState message={gapError} onRetry={loadSkillGap} />
              ) : skillGapReport ? (
                <>
                  {/* KPI Grid */}
                  <div className={styles.kpiGrid}>
                    <div className={styles.kpiCard}>
                      <div className={styles.kpiHeader}>
                        <span>Target Readiness</span>
                        <Award size={18} style={{ color: '#3b82f6' }} />
                      </div>
                      <div className={styles.kpiValue}>
                        {skillGapReport.readiness_percentage.toFixed(0)}%
                      </div>
                      <div className={styles.readinessBarContainer}>
                        <div className={styles.readinessBarTrack}>
                          <div
                            className={styles.readinessBarFill}
                            style={{ width: `${Math.min(100, skillGapReport.readiness_percentage)}%` }}
                          />
                        </div>
                      </div>
                      <div className={styles.kpiSubtext}>Overall competency readiness score</div>
                    </div>

                    <div className={styles.kpiCard}>
                      <div className={styles.kpiHeader}>
                        <span>Critical Skills Met</span>
                        <CheckCircle2 size={18} style={{ color: '#10b981' }} />
                      </div>
                      <div className={styles.kpiValue}>
                        {skillGapReport.critical_skills_met} / {skillGapReport.total_critical_skills}
                      </div>
                      <div className={styles.kpiSubtext}>Essential target competencies</div>
                    </div>

                    <div className={styles.kpiCard}>
                      <div className={styles.kpiHeader}>
                        <span>Target Skills</span>
                        <Compass size={18} style={{ color: '#6366f1' }} />
                      </div>
                      <div className={styles.kpiValue}>{skillGapReport.total_target_skills}</div>
                      <div className={styles.kpiSubtext}>Total skills required by objective</div>
                    </div>

                    <div className={styles.kpiCard}>
                      <div className={styles.kpiHeader}>
                        <span>Coursework Skills</span>
                        <BookOpen size={18} style={{ color: '#059669' }} />
                      </div>
                      <div className={styles.kpiValue}>{skillGapReport.acquired_skills.length}</div>
                      <div className={styles.kpiSubtext}>Skills earned from completed courses</div>
                    </div>
                  </div>

                  {/* Satisfied Skills */}
                  <div className={styles.skillsSection}>
                    <div className={styles.sectionHeader}>
                      <h3 className={styles.sectionTitle}>
                        <CheckCircle2 size={18} style={{ color: '#10b981' }} />
                        Satisfied Skills ({skillGapReport.satisfied_skills.length})
                      </h3>
                    </div>
                    {skillGapReport.satisfied_skills.length === 0 ? (
                      <EmptyState
                        title="No satisfied skills yet"
                        description="Complete relevant coursework to demonstrate required competencies."
                      />
                    ) : (
                      <div className={styles.skillsGrid}>
                        {skillGapReport.satisfied_skills.map((req) => {
                          const acquired = skillGapReport.acquired_skills.find(
                            (a) => a.skill_code === req.skill_code
                          );
                          return (
                            <div
                              key={req.skill_id}
                              className={`${styles.skillCard} ${styles.skillCardSatisfied}`}
                            >
                              <div className={styles.skillTopRow}>
                                <span className={styles.skillName}>{req.skill_name}</span>
                                <Badge variant="success">Satisfied</Badge>
                              </div>
                              <div className={styles.skillMeta}>
                                <span>Code: {req.skill_code}</span>
                                <span>•</span>
                                <span>Req: {req.min_proficiency}</span>
                                <span>•</span>
                                <span>Earned: {req.current_proficiency}</span>
                              </div>
                              {acquired && acquired.source_courses.length > 0 && (
                                <div className={styles.sourceCourses}>
                                  <GraduationCap size={14} />
                                  <span>Acquired in: {acquired.source_courses.join(', ')}</span>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  {/* Partial Proficiency Gaps */}
                  {skillGapReport.proficiency_gaps.length > 0 && (
                    <div className={styles.skillsSection}>
                      <div className={styles.sectionHeader}>
                        <h3 className={styles.sectionTitle}>
                          <AlertCircle size={18} style={{ color: '#f59e0b' }} />
                          Proficiency Gaps ({skillGapReport.proficiency_gaps.length})
                        </h3>
                      </div>
                      <div className={styles.skillsGrid}>
                        {skillGapReport.proficiency_gaps.map((req) => (
                          <div
                            key={req.skill_id}
                            className={`${styles.skillCard} ${styles.skillCardGap}`}
                          >
                            <div className={styles.skillTopRow}>
                              <span className={styles.skillName}>{req.skill_name}</span>
                              <Badge variant="warning">Partial Level</Badge>
                            </div>
                            <div className={styles.skillMeta}>
                              <span>Target: {req.min_proficiency}</span>
                              <span>•</span>
                              <span>Current: {req.current_proficiency}</span>
                              {req.is_critical && (
                                <>
                                  <span>•</span>
                                  <Badge variant="danger" size="sm">
                                    Critical
                                  </Badge>
                                </>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Missing Skills */}
                  {skillGapReport.missing_skills.length > 0 && (
                    <div className={styles.skillsSection}>
                      <div className={styles.sectionHeader}>
                        <h3 className={styles.sectionTitle}>
                          <HelpCircle size={18} style={{ color: '#ef4444' }} />
                          Missing Skills ({skillGapReport.missing_skills.length})
                        </h3>
                      </div>
                      <div className={styles.skillsGrid}>
                        {skillGapReport.missing_skills.map((req) => (
                          <div
                            key={req.skill_id}
                            className={`${styles.skillCard} ${styles.skillCardMissing}`}
                          >
                            <div className={styles.skillTopRow}>
                              <span className={styles.skillName}>{req.skill_name}</span>
                              <Badge variant="danger">Missing</Badge>
                            </div>
                            <div className={styles.skillMeta}>
                              <span>Required: {req.min_proficiency}</span>
                              <span>•</span>
                              <span>Category: {req.skill_category}</span>
                              {req.is_critical && (
                                <>
                                  <span>•</span>
                                  <Badge variant="danger" size="sm">
                                    Critical
                                  </Badge>
                                </>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : null}
            </>
          )}

          {/* TAB 2: COURSE RECOMMENDATIONS */}
          {activeTab === 'recommendations' && (
            <>
              {isRecsLoading ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  <Skeleton height="80px" />
                  <Skeleton height="120px" />
                  <Skeleton height="120px" />
                </div>
              ) : recsError ? (
                <ErrorState message={recsError} onRetry={loadRecommendations} />
              ) : recommendations.length === 0 ? (
                <EmptyState
                  title="No course recommendations available"
                  description="All target competencies have been satisfied, or no course mappings exist for missing skills."
                />
              ) : (
                <div className={styles.recommendationList}>
                  {recommendations.map((rec) => (
                    <div key={rec.course_id} className={styles.recommendationCard}>
                      <div className={styles.recHeader}>
                        <div className={styles.recCourseInfo}>
                          <div className={styles.recCourseTitle}>
                            {rec.course_code}: {rec.course_title}
                          </div>
                          <div className={styles.recBadges}>
                            {/* Degree vs Career Elective Badge */}
                            {rec.recommendation_type === 'DEGREE_AND_CAREER' ? (
                              <Badge variant="teal">Degree Requirement & Career</Badge>
                            ) : (
                              <Badge variant="neutral">Career Elective</Badge>
                            )}

                            {/* Prerequisite Eligibility Badge */}
                            {rec.is_prerequisite_eligible ? (
                              <Badge variant="success">Prerequisites Met</Badge>
                            ) : (
                              <Badge variant="warning">
                                Prerequisites Pending ({rec.prerequisite_status_message})
                              </Badge>
                            )}

                            <span style={{ fontSize: '0.8125rem', color: '#64748b' }}>
                              Credits: {rec.credits}
                            </span>
                            <span style={{ fontSize: '0.8125rem', color: '#64748b' }}>
                              Relevance: {(rec.relevance_score * 100).toFixed(0)}%
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Explanation */}
                      <div className={styles.recExplanation}>{rec.explanation}</div>

                      {/* Skills Covered */}
                      <div className={styles.skillsCoveredRow}>
                        <span>Target Skills Covered:</span>
                        {rec.skills_covered.map((sc) => (
                          <span key={sc.skill_id} className={styles.skillPill}>
                            {sc.skill_name} ({sc.proficiency_level})
                            {sc.is_critical && ' ★'}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          {/* TAB 3: TAXONOMY & MAPPINGS */}
          {activeTab === 'taxonomy' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
              {isTaxonomyLoading ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  <Skeleton height="40px" />
                  <Skeleton height="150px" />
                  <Skeleton height="150px" />
                </div>
              ) : (
                <>
                  {/* Skills Taxonomy Section */}
                  <div>
                    <div className={styles.taxonomyToolbar}>
                      <div className={styles.filterControls}>
                        <input
                          type="text"
                          placeholder="Search skills by code or name..."
                          className={styles.searchInput}
                          value={skillSearchQuery}
                          onChange={(e) => setSkillSearchQuery(e.target.value)}
                        />
                        <select
                          className={styles.selectInput}
                          style={{ minWidth: '180px' }}
                          value={skillCategoryFilter}
                          onChange={(e) => setSkillCategoryFilter(e.target.value)}
                        >
                          <option value="ALL">All Categories</option>
                          <option value="TECHNICAL">Technical</option>
                          <option value="SOFT_SKILL">Soft Skill</option>
                          <option value="DOMAIN_KNOWLEDGE">Domain Knowledge</option>
                          <option value="TOOL_OR_PLATFORM">Tool / Platform</option>
                        </select>
                      </div>

                      {canManage && (
                        <Button
                          size="sm"
                          variant="primary"
                          leftIcon={<Plus size={14} />}
                          onClick={() => setIsAddSkillOpen(true)}
                        >
                          Add Skill
                        </Button>
                      )}
                    </div>

                    <Table
                      columns={skillColumns}
                      data={filteredSkills}
                      keyExtractor={(s) => s.id}
                      caption="Master Skill Taxonomy"
                      emptyState={<EmptyState title="No skills found" />}
                    />
                  </div>

                  {/* Course to Skill Mappings Section */}
                  <div>
                    <h3 className={styles.sectionTitle} style={{ marginBottom: '1rem' }}>
                      Course-to-Skill Mappings
                    </h3>
                    <Table
                      columns={mappingColumns}
                      data={courseMappings}
                      keyExtractor={(m) => m.id}
                      caption="Institution Course Skill Mappings"
                      emptyState={<EmptyState title="No course-to-skill mappings defined" />}
                    />
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Add Skill Dialog (Coordinator / Admin) */}
      <Dialog
        isOpen={isAddSkillOpen}
        onClose={() => setIsAddSkillOpen(false)}
        title="Add New Competency / Skill"
      >
        <form onSubmit={handleCreateSkillSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <Input
            label="Skill Code"
            placeholder="e.g. PYTHON_PROG"
            value={newSkillCode}
            onChange={(e) => setNewSkillCode(e.target.value)}
            required
          />
          <Input
            label="Skill Name"
            placeholder="e.g. Python Programming"
            value={newSkillName}
            onChange={(e) => setNewSkillName(e.target.value)}
            required
          />
          <Select
            label="Category"
            value={newSkillCategory}
            onChange={(e) => setNewSkillCategory(e.target.value as SkillCategory)}
            options={[
              { value: 'TECHNICAL', label: 'Technical' },
              { value: 'SOFT_SKILL', label: 'Soft Skill' },
              { value: 'DOMAIN_KNOWLEDGE', label: 'Domain Knowledge' },
              { value: 'TOOL_OR_PLATFORM', label: 'Tool / Platform' },
            ]}
          />
          <Input
            label="Description"
            placeholder="Brief description of competency"
            value={newSkillDescription}
            onChange={(e) => setNewSkillDescription(e.target.value)}
          />

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem' }}>
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsAddSkillOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              isLoading={isSubmittingSkill}
            >
              Save Skill
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
};
