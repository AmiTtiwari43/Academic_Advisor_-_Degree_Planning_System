import React, { useEffect, useState } from 'react';
import {
  curriculumApi,
  CurriculumVersionDetail,
  Programme,
  Course,
  ValidationReport,
} from '../api/curriculum';
import { RuleBuilderModal } from '../components/curriculum/RuleBuilderModal';
import { PublishPreviewModal } from '../components/curriculum/PublishPreviewModal';
import { VersionDiffModal } from '../components/curriculum/VersionDiffModal';
import { SectionSearchBar } from '../components/Search';
import styles from './CurriculumWorkspacePage.module.css';

export const CurriculumWorkspacePage: React.FC = () => {
  const [programmes, setProgrammes] = useState<Programme[]>([]);
  const [selectedProgrammeId, setSelectedProgrammeId] = useState<string>('');
  const [selectedVersionId, setSelectedVersionId] = useState<string>('');
  const [versionDetail, setVersionDetail] = useState<CurriculumVersionDetail | null>(null);
  const [allCourses, setAllCourses] = useState<Course[]>([]);
  const [activeTab, setActiveTab] = useState<'groups' | 'courses' | 'rules'>('groups');

  // Loading and alerts
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [feedbackMsg, setFeedbackMsg] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);
  const [validationReport, setValidationReport] = useState<ValidationReport | null>(null);

  // Modals state
  const [isRuleModalOpen, setIsRuleModalOpen] = useState<boolean>(false);
  const [isPublishModalOpen, setIsPublishModalOpen] = useState<boolean>(false);
  const [isDiffModalOpen, setIsDiffModalOpen] = useState<boolean>(false);

  // Search filters
  const [courseSearch, setCourseSearch] = useState<string>('');
  const [ruleSearch, setRuleSearch] = useState<string>('');
  const [groupSearch, setGroupSearch] = useState<string>('');

  // Initial fetch: programmes & courses
  const loadData = async () => {
    setIsLoading(true);
    try {
      const [progs, courses] = await Promise.all([
        curriculumApi.getProgrammes(),
        curriculumApi.getCourses(),
      ]);
      const progsList = Array.isArray(progs)
        ? progs
        : (progs as unknown as { results?: typeof progs })?.results || [];
      const coursesList = Array.isArray(courses)
        ? courses
        : (courses as unknown as { results?: typeof courses })?.results || [];
      setProgrammes(progsList);
      setAllCourses(coursesList);

      if (progsList.length > 0 && !selectedProgrammeId) {
        setSelectedProgrammeId(progsList[0].id);
        const versions = progsList[0].curriculum_versions || [];
        if (versions.length > 0) {
          setSelectedVersionId(versions[0].id);
        }
      }
    } catch (err: unknown) {
      setFeedbackMsg({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to load curriculum data',
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Fetch version detail when selectedVersionId changes
  const loadVersionDetail = async (verId: string) => {
    if (!verId) return;
    try {
      const detail = await curriculumApi.getCurriculumVersion(verId);
      setVersionDetail(detail);
      setValidationReport(null);
    } catch (err: unknown) {
      setFeedbackMsg({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to load version details',
      });
    }
  };

  useEffect(() => {
    if (selectedVersionId) {
      loadVersionDetail(selectedVersionId);
    }
  }, [selectedVersionId]);

  const currentProgramme = programmes.find((p) => p.id === selectedProgrammeId);
  const programmeVersions = currentProgramme?.curriculum_versions || [];

  const handleProgrammeChange = (progId: string) => {
    setSelectedProgrammeId(progId);
    const prog = programmes.find((p) => p.id === progId);
    const versions = prog?.curriculum_versions || [];
    if (versions.length > 0) {
      setSelectedVersionId(versions[0].id);
    } else {
      setSelectedVersionId('');
      setVersionDetail(null);
    }
  };

  const handleValidate = async () => {
    if (!selectedVersionId) return;
    try {
      const report = await curriculumApi.validateVersion(selectedVersionId);
      setValidationReport(report);
      setFeedbackMsg({
        type: report.is_valid ? 'success' : 'error',
        text: report.is_valid
          ? 'Validation passed! No structural errors detected.'
          : `Validation detected ${report.errors.length} errors.`,
      });
    } catch (err: unknown) {
      setFeedbackMsg({
        type: 'error',
        text: err instanceof Error ? err.message : 'Validation failed',
      });
    }
  };

  const handleClone = async () => {
    if (!selectedVersionId) return;
    try {
      const cloned = await curriculumApi.cloneVersion(selectedVersionId);
      setFeedbackMsg({
        type: 'success',
        text: `Successfully created new draft version v${cloned.version_number}!`,
      });
      await loadData();
      setSelectedVersionId(cloned.id);
    } catch (err: unknown) {
      setFeedbackMsg({
        type: 'error',
        text: err instanceof Error ? err.message : 'Cloning failed',
      });
    }
  };

  const handleCreateNewDraft = async () => {
    if (!selectedProgrammeId) return;
    try {
      const newV = await curriculumApi.createProgrammeVersion(selectedProgrammeId, {
        academic_year: '2026-2027',
        total_credits_required: 120.0,
        min_cgpa_required: 5.0,
      });
      setFeedbackMsg({
        type: 'success',
        text: `Draft version v${newV.version_number} created successfully.`,
      });
      await loadData();
      setSelectedVersionId(newV.id);
    } catch (err: unknown) {
      setFeedbackMsg({
        type: 'error',
        text: err instanceof Error ? err.message : 'Draft creation failed',
      });
    }
  };

  const handleSaveRule = async (ruleJson: Record<string, unknown>, description: string) => {
    if (!selectedVersionId) return;
    // Find course from rule or default
    const targetCourse = (ruleJson.course_code as string) || (allCourses[0]?.code ?? 'CS-101');
    const courseObj = allCourses.find((c) => c.code === targetCourse);
    if (!courseObj) {
      setFeedbackMsg({ type: 'error', text: `Course ${targetCourse} not found in catalog.` });
      return;
    }

    try {
      await curriculumApi.createPrerequisiteRule({
        curriculum_version: selectedVersionId,
        course: courseObj.id,
        rule_json: ruleJson,
        description,
      });
      setFeedbackMsg({ type: 'success', text: `Prerequisite rule saved for ${targetCourse}.` });
      loadVersionDetail(selectedVersionId);
    } catch (err: unknown) {
      setFeedbackMsg({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to save prerequisite rule',
      });
    }
  };

  const filteredCourses = allCourses.filter(
    (c) =>
      c.code.toLowerCase().includes(courseSearch.toLowerCase()) ||
      c.title.toLowerCase().includes(courseSearch.toLowerCase())
  );

  // Requirement groups filter
  const filteredGroups = (versionDetail?.requirement_groups || []).filter((g) => {
    if (!groupSearch.trim()) return true;
    const q = groupSearch.toLowerCase();
    const matchesName = g.name.toLowerCase().includes(q);
    const matchesCourse = (g.group_courses || []).some(
      (c) =>
        c.course_code.toLowerCase().includes(q) ||
        c.course_title.toLowerCase().includes(q)
    );
    return matchesName || matchesCourse;
  });

  // Prerequisite rules filter
  const filteredRules = (versionDetail?.prerequisite_rules || []).filter((r) => {
    if (!ruleSearch.trim()) return true;
    const q = ruleSearch.toLowerCase();
    const course = allCourses.find((c) => c.id === r.course);
    const code = (course?.code || '').toLowerCase();
    const title = (course?.title || '').toLowerCase();
    return code.includes(q) || title.includes(q) || JSON.stringify(r.rule_json).toLowerCase().includes(q);
  });

  return (
    <div className={styles.pageContainer}>
      {/* Page Title & Breadcrumb */}
      <div className={styles.pageHeader}>
        <div>
          <span className={styles.preTitle}>Academic Catalogue &amp; Specifications</span>
          <h1 className={styles.title}>
            Curriculum &amp; Requirement Workspace
          </h1>
          <p className={styles.subtitle}>
            Author, validate, preview, and publish immutable curriculum versions with deterministic rules.
          </p>
        </div>

        {/* Global Notifications */}
        {feedbackMsg && (
          <div
            style={{
              padding: '0.6rem 1rem',
              borderRadius: '8px',
              fontSize: '0.85rem',
              fontWeight: 500,
              backgroundColor:
                feedbackMsg.type === 'success'
                  ? '#DCFCE7'
                  : feedbackMsg.type === 'error'
                  ? '#FEE2E2'
                  : '#E0F2FE',
              color:
                feedbackMsg.type === 'success'
                  ? '#166534'
                  : feedbackMsg.type === 'error'
                  ? '#991B1B'
                  : '#0369A1',
              border: `1px solid ${
                feedbackMsg.type === 'success'
                  ? '#86EFAC'
                  : feedbackMsg.type === 'error'
                  ? '#FCA5A5'
                  : '#BAE6FD'
              }`,
            }}
          >
            {feedbackMsg.text}
          </div>
        )}

        {isLoading && (
          <div
            role="status"
            aria-live="polite"
            style={{
              padding: '0.6rem 1rem',
              borderRadius: '8px',
              fontSize: '0.85rem',
              fontWeight: 500,
              backgroundColor: '#F1F5F9',
              color: '#475569',
              border: '1px solid #CBD5E1',
            }}
          >
            Loading curriculum data...
          </div>
        )}
      </div>

      {/* Programme & Version Header Bar */}
      <div className={styles.controlCard}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', flexWrap: 'wrap' }}>
          {/* Programme Dropdown */}
          <div className={styles.controlGroup}>
            <label className={styles.controlLabel}>
              Degree Programme
            </label>
            <select
              value={selectedProgrammeId}
              onChange={(e) => handleProgrammeChange(e.target.value)}
              className={styles.selectInput}
              style={{ minWidth: '260px' }}
            >
              {programmes.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.code} - {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Version Selector */}
          <div className={styles.controlGroup}>
            <label className={styles.controlLabel}>
              Curriculum Version
            </label>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <select
                value={selectedVersionId}
                onChange={(e) => setSelectedVersionId(e.target.value)}
                disabled={programmeVersions.length === 0}
                className={styles.selectInput}
                style={{ minWidth: '180px' }}
              >
                {programmeVersions.map((v) => (
                  <option key={v.id} value={v.id}>
                    v{v.version_number} ({v.academic_year}) - [{v.status}]
                  </option>
                ))}
              </select>

              {programmeVersions.length === 0 && (
                <button
                  onClick={handleCreateNewDraft}
                  style={{
                    padding: '0.5rem 0.85rem',
                    backgroundColor: '#2563EB',
                    color: '#FFFFFF',
                    border: 'none',
                    borderRadius: '6px',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Create Initial Draft
                </button>
              )}
            </div>
          </div>

          {/* Status Badge */}
          {versionDetail && (
            <div>
              <span style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748B', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
                Status
              </span>
              <span
                style={{
                  display: 'inline-block',
                  padding: '0.35rem 0.75rem',
                  borderRadius: '999px',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  backgroundColor:
                    versionDetail.status === 'PUBLISHED'
                      ? '#DCFCE7'
                      : versionDetail.status === 'DRAFT'
                      ? '#FEF3C7'
                      : '#F1F5F9',
                  color:
                    versionDetail.status === 'PUBLISHED'
                      ? '#166534'
                      : versionDetail.status === 'DRAFT'
                      ? '#92400E'
                      : '#475569',
                  border: `1px solid ${
                    versionDetail.status === 'PUBLISHED'
                      ? '#86EFAC'
                      : versionDetail.status === 'DRAFT'
                      ? '#FCD34D'
                      : '#CBD5E1'
                  }`,
                }}
              >
                {versionDetail.status}
                {versionDetail.status === 'PUBLISHED' ? ' (Immutable)' : ' (Editable)'}
              </span>
            </div>
          )}
        </div>

        {/* Action Toolbar */}
        {versionDetail && (
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button
              onClick={handleValidate}
              style={{
                padding: '0.5rem 0.9rem',
                backgroundColor: '#F8FAFC',
                border: '1px solid #CBD5E1',
                borderRadius: '6px',
                fontSize: '0.85rem',
                fontWeight: 600,
                color: '#334155',
                cursor: 'pointer',
              }}
            >
              Validate Rules
            </button>

            {versionDetail.is_editable && (
              <button
                onClick={() => setIsPublishModalOpen(true)}
                style={{
                  padding: '0.5rem 0.9rem',
                  backgroundColor: '#166534',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  color: '#FFFFFF',
                  cursor: 'pointer',
                }}
              >
                Publish Version
              </button>
            )}

            <button
              onClick={handleClone}
              style={{
                padding: '0.5rem 0.9rem',
                backgroundColor: '#2563EB',
                border: 'none',
                borderRadius: '6px',
                fontSize: '0.85rem',
                fontWeight: 600,
                color: '#FFFFFF',
                cursor: 'pointer',
              }}
            >
              Clone to Draft
            </button>

            {programmeVersions.length > 1 && (
              <button
                onClick={() => setIsDiffModalOpen(true)}
                style={{
                  padding: '0.5rem 0.9rem',
                  backgroundColor: '#F8FAFC',
                  border: '1px solid #CBD5E1',
                  borderRadius: '6px',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  color: '#334155',
                  cursor: 'pointer',
                }}
              >
                Compare Versions
              </button>
            )}
          </div>
        )}
      </div>

      {/* Validation Alert Box if present */}
      {validationReport && (
        <div
          style={{
            padding: '1rem 1.25rem',
            backgroundColor: validationReport.is_valid ? '#F0FDF4' : '#FEF2F2',
            border: `1px solid ${validationReport.is_valid ? '#86EFAC' : '#FCA5A5'}`,
            borderRadius: '8px',
            marginBottom: '1.5rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontWeight: 700, fontSize: '0.9rem', color: validationReport.is_valid ? '#166534' : '#991B1B' }}>
              {validationReport.is_valid ? 'Validation Report: Ready for Publishing' : `Validation Issues (${validationReport.errors.length} Errors)`}
            </span>
            <button
              onClick={() => setValidationReport(null)}
              style={{ background: 'none', border: 'none', color: '#64748B', cursor: 'pointer', fontSize: '0.8rem' }}
            >
              Dismiss
            </button>
          </div>
          {validationReport.errors.length > 0 && (
            <ul style={{ margin: '0.5rem 0 0', paddingLeft: '1.25rem', fontSize: '0.825rem', color: '#B91C1C' }}>
              {validationReport.errors.map((e, idx) => (
                <li key={idx}><strong>{e.code}:</strong> {e.message}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Main Workspace Navigation Tabs */}
      <div className={styles.tabsBar}>
        <button
          onClick={() => setActiveTab('groups')}
          className={`${styles.tabBtn} ${activeTab === 'groups' ? styles.tabBtnActive : ''}`}
        >
          Requirement Groups Hierarchy
        </button>
        <button
          onClick={() => setActiveTab('courses')}
          className={`${styles.tabBtn} ${activeTab === 'courses' ? styles.tabBtnActive : ''}`}
        >
          Course Catalogue
        </button>
        <button
          onClick={() => setActiveTab('rules')}
          className={`${styles.tabBtn} ${activeTab === 'rules' ? styles.tabBtnActive : ''}`}
        >
          Prerequisite Rules &amp; Test Simulator
        </button>
      </div>

      {/* Tab 1: Requirement Groups Tree */}
      {activeTab === 'groups' && versionDetail && (
        <div style={{ backgroundColor: '#FFFFFF', borderRadius: '8px', border: '1px solid #E2E8F0', padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#0F172A', fontWeight: 600 }}>
              Curriculum Requirement Structure
            </h3>
            <span style={{ fontSize: '0.85rem', color: '#64748B' }}>
              Total Required: <strong>{versionDetail.total_credits_required} Credits</strong> | Min CGPA: <strong>{versionDetail.min_cgpa_required} (10.0 Scale)</strong>
            </span>
          </div>

          <div style={{ marginBottom: '1.25rem' }}>
            <SectionSearchBar
              value={groupSearch}
              onChange={setGroupSearch}
              placeholder="Search requirement groups by name or course code..."
              badgeCount={filteredGroups.length}
            />
          </div>

          {filteredGroups.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem', backgroundColor: '#F8FAFC', borderRadius: '8px', border: '1px dashed #CBD5E1' }}>
              <p style={{ margin: '0 0 0.5rem', color: '#64748B' }}>No requirement groups match your search criteria.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {filteredGroups.map((group) => (
                <div
                  key={group.id}
                  style={{
                    border: '1px solid #E2E8F0',
                    borderRadius: '8px',
                    padding: '1.25rem',
                    backgroundColor: '#F8FAFC',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
                    <div>
                      <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: '#1E293B' }}>
                        {group.name}
                      </h4>
                      <span style={{ fontSize: '0.8rem', color: '#64748B' }}>
                        Type: <span style={{ fontWeight: 600 }}>{group.group_type}</span> | Minimum Required: <span style={{ fontWeight: 600 }}>{group.min_credits} cr</span>
                      </span>
                    </div>
                  </div>

                  {/* Group Courses Table */}
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', backgroundColor: '#FFFFFF', borderRadius: '6px', overflow: 'hidden' }}>
                    <thead>
                      <tr style={{ backgroundColor: '#F1F5F9', borderBottom: '1px solid #E2E8F0', textAlign: 'left' }}>
                        <th style={{ padding: '0.5rem 0.75rem', color: '#475569' }}>Course Code</th>
                        <th style={{ padding: '0.5rem 0.75rem', color: '#475569' }}>Course Title</th>
                        <th style={{ padding: '0.5rem 0.75rem', color: '#475569' }}>Credits</th>
                        <th style={{ padding: '0.5rem 0.75rem', color: '#475569' }}>Requirement Type</th>
                      </tr>
                    </thead>
                    <tbody>
                      {group.group_courses.length === 0 ? (
                        <tr>
                          <td colSpan={4} style={{ padding: '1rem', textAlign: 'center', color: '#94A3B8' }}>
                            No courses currently assigned to this requirement group.
                          </td>
                        </tr>
                      ) : (
                        group.group_courses.map((gc) => (
                          <tr key={gc.id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                            <td style={{ padding: '0.5rem 0.75rem', fontWeight: 600, color: '#0F172A' }}>{gc.course_code}</td>
                            <td style={{ padding: '0.5rem 0.75rem', color: '#334155' }}>{gc.course_title}</td>
                            <td style={{ padding: '0.5rem 0.75rem', color: '#334155' }}>{gc.course_credits} cr</td>
                            <td style={{ padding: '0.5rem 0.75rem' }}>
                              <span style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem', borderRadius: '4px', backgroundColor: gc.is_mandatory ? '#DCFCE7' : '#FEF3C7', color: gc.is_mandatory ? '#166534' : '#92400E' }}>
                                {gc.is_mandatory ? 'Mandatory' : 'Elective'}
                              </span>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Course Catalogue Table */}
      {activeTab === 'courses' && (
        <div style={{ backgroundColor: '#FFFFFF', borderRadius: '8px', border: '1px solid #E2E8F0', padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '1rem' }}>
            <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#0F172A', fontWeight: 600 }}>
              Institution Course Catalogue
            </h3>
            <div style={{ flex: 1, maxWidth: '380px' }}>
              <SectionSearchBar
                value={courseSearch}
                onChange={setCourseSearch}
                placeholder="Search by code or title..."
                badgeCount={filteredCourses.length}
              />
            </div>
          </div>

          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ backgroundColor: '#F8FAFC', borderBottom: '2px solid #E2E8F0', textAlign: 'left' }}>
                <th style={{ padding: '0.6rem 0.75rem', color: '#475569' }}>Code</th>
                <th style={{ padding: '0.6rem 0.75rem', color: '#475569' }}>Course Title</th>
                <th style={{ padding: '0.6rem 0.75rem', color: '#475569' }}>Credits</th>
                <th style={{ padding: '0.6rem 0.75rem', color: '#475569' }}>Default Category</th>
                <th style={{ padding: '0.6rem 0.75rem', color: '#475569' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredCourses.map((c) => (
                <tr key={c.id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                  <td style={{ padding: '0.6rem 0.75rem', fontWeight: 600, color: '#0F172A' }}>{c.code}</td>
                  <td style={{ padding: '0.6rem 0.75rem', color: '#334155' }}>{c.title}</td>
                  <td style={{ padding: '0.6rem 0.75rem', color: '#334155' }}>{c.credits} cr</td>
                  <td style={{ padding: '0.6rem 0.75rem', color: '#64748B' }}>{c.default_credit_category_code || 'General'}</td>
                  <td style={{ padding: '0.6rem 0.75rem' }}>
                    <span style={{ fontSize: '0.75rem', color: c.is_active ? '#166534' : '#64748B' }}>
                      {c.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab 3: Prerequisite Rules & Simulator */}
      {activeTab === 'rules' && versionDetail && (
        <div style={{ backgroundColor: '#FFFFFF', borderRadius: '8px', border: '1px solid #E2E8F0', padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <div>
              <h3 style={{ margin: '0 0 0.25rem', fontSize: '1.1rem', color: '#0F172A', fontWeight: 600 }}>
                Prerequisite Rules in Current Version
              </h3>
              <p style={{ margin: 0, fontSize: '0.85rem', color: '#64748B' }}>
                All rules adhere to Grammar v1 and are evaluated with Kleene 3-valued logic.
              </p>
            </div>
            {versionDetail.is_editable && (
              <button
                onClick={() => setIsRuleModalOpen(true)}
                style={{
                  padding: '0.55rem 1rem',
                  backgroundColor: '#2563EB',
                  color: '#FFFFFF',
                  border: 'none',
                  borderRadius: '6px',
                  fontWeight: 600,
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                }}
              >
                + Author / Test New Rule
              </button>
            )}
          </div>

          <div style={{ marginBottom: '1.25rem' }}>
            <SectionSearchBar
              value={ruleSearch}
              onChange={setRuleSearch}
              placeholder="Search prerequisite rules by course code or logic..."
              badgeCount={filteredRules.length}
            />
          </div>

          {filteredRules.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem', backgroundColor: '#F8FAFC', borderRadius: '8px', border: '1px dashed #CBD5E1' }}>
              <p style={{ margin: '0 0 0.5rem', color: '#64748B' }}>No prerequisite rules match your search criteria.</p>
              <button
                onClick={() => setIsRuleModalOpen(true)}
                style={{
                  padding: '0.5rem 1rem',
                  backgroundColor: '#2563EB',
                  color: '#FFFFFF',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Open Rule Authoring Studio
              </button>
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ backgroundColor: '#F8FAFC', borderBottom: '2px solid #E2E8F0', textAlign: 'left' }}>
                  <th style={{ padding: '0.6rem 0.75rem', color: '#475569' }}>Target Course</th>
                  <th style={{ padding: '0.6rem 0.75rem', color: '#475569' }}>Rule Type</th>
                  <th style={{ padding: '0.6rem 0.75rem', color: '#475569' }}>Description</th>
                  <th style={{ padding: '0.6rem 0.75rem', color: '#475569' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredRules.map((r) => (
                  <tr key={r.id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                    <td style={{ padding: '0.6rem 0.75rem', fontWeight: 600, color: '#0F172A' }}>
                      {r.course_code} - {r.course_title}
                    </td>
                    <td style={{ padding: '0.6rem 0.75rem' }}>
                      <code style={{ backgroundColor: '#F1F5F9', padding: '0.2rem 0.4rem', borderRadius: '4px', fontSize: '0.75rem' }}>
                        {String(r.rule_json.type || 'rule')}
                      </code>
                    </td>
                    <td style={{ padding: '0.6rem 0.75rem', color: '#475569' }}>
                      {r.description || 'Prerequisite rule'}
                    </td>
                    <td style={{ padding: '0.6rem 0.75rem' }}>
                      <button
                        onClick={() => setIsRuleModalOpen(true)}
                        style={{
                          padding: '0.35rem 0.65rem',
                          backgroundColor: '#F8FAFC',
                          border: '1px solid #CBD5E1',
                          borderRadius: '4px',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          cursor: 'pointer',
                          color: '#2563EB',
                        }}
                      >
                        Simulate in Harness
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Modals */}
      <RuleBuilderModal
        isOpen={isRuleModalOpen}
        onClose={() => setIsRuleModalOpen(false)}
        onSaveRule={handleSaveRule}
        availableCourses={allCourses.map((c) => c.code)}
      />

      <PublishPreviewModal
        versionId={selectedVersionId}
        isOpen={isPublishModalOpen}
        onClose={() => setIsPublishModalOpen(false)}
        onPublishedSuccess={() => {
          loadData();
          loadVersionDetail(selectedVersionId);
          setFeedbackMsg({
            type: 'success',
            text: 'Curriculum version successfully published! Status is now permanently immutable.',
          });
        }}
      />

      <VersionDiffModal
        currentVersionId={selectedVersionId}
        allVersions={programmeVersions}
        isOpen={isDiffModalOpen}
        onClose={() => setIsDiffModalOpen(false)}
      />
    </div>
  );
};
