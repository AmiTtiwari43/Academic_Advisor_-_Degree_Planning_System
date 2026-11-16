import React, { useState } from 'react';
import { curriculumApi, RuleHarnessResult } from '../../api/curriculum';

interface RuleBuilderModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaveRule?: (ruleJson: Record<string, unknown>, description: string) => void;
  availableCourses: string[];
}

export const RuleBuilderModal: React.FC<RuleBuilderModalProps> = ({
  isOpen,
  onClose,
  onSaveRule,
  availableCourses,
}) => {
  const [activeTab, setActiveTab] = useState<'builder' | 'harness'>('builder');

  // Rule Builder State
  const [operator, setOperator] = useState<string>('course_completed');
  const [targetCourse, setTargetCourse] = useState<string>(availableCourses[0] || 'CS-101');
  const [minGrade, setMinGrade] = useState<string>('C');
  const [minCredits, setMinCredits] = useState<number>(30);
  const [minCgpa, setMinCgpa] = useState<number>(6.0);
  const [ruleDescription, setRuleDescription] = useState<string>('Standard Course Prerequisite');

  // Multi-condition state for all_of
  const [secondaryCourse, setSecondaryCourse] = useState<string>(availableCourses[1] || 'MATH-151');
  const [secondaryGrade, setSecondaryGrade] = useState<string>('C');

  // Test Harness State
  const [testStudentId, setTestStudentId] = useState<string>('STU-9921');
  const [testCompletedCode, setTestCompletedCode] = useState<string>('CS-101');
  const [testGrade, setTestGrade] = useState<string>('B');
  const [testCredits, setTestCredits] = useState<number>(32);
  const [testCgpa, setTestCgpa] = useState<number>(7.5);
  const [isTestInProgress, setIsTestInProgress] = useState<boolean>(false);

  // Simulation Result
  const [harnessResult, setHarnessResult] = useState<RuleHarnessResult | null>(null);
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [simError, setSimError] = useState<string | null>(null);

  if (!isOpen) return null;

  // Build the structured JSON AST
  const generateAst = (): Record<string, unknown> => {
    if (operator === 'all_of') {
      return {
        schema_version: 1,
        type: 'all_of',
        conditions: [
          {
            type: 'course_completed',
            course_code: targetCourse,
            min_grade: minGrade,
          },
          {
            type: 'course_completed',
            course_code: secondaryCourse,
            min_grade: secondaryGrade,
          },
        ],
      };
    }
    if (operator === 'credits_completed') {
      return {
        schema_version: 1,
        type: 'credits_completed',
        min_credits: Number(minCredits),
      };
    }
    if (operator === 'cgpa_min') {
      return {
        schema_version: 1,
        type: 'cgpa_min',
        value: Number(minCgpa),
      };
    }
    if (operator === 'corequisite') {
      return {
        schema_version: 1,
        type: 'corequisite',
        course_code: targetCourse,
      };
    }
    if (operator === 'anti_requisite') {
      return {
        schema_version: 1,
        type: 'anti_requisite',
        course_code: targetCourse,
      };
    }
    // Default: course_completed
    return {
      schema_version: 1,
      type: 'course_completed',
      course_code: targetCourse,
      min_grade: minGrade,
    };
  };

  const currentAst = generateAst();

  const handleSimulate = async () => {
    setIsSimulating(true);
    setSimError(null);
    setHarnessResult(null);

    const contextPayload = {
      student_id: testStudentId,
      completed_courses: [
        {
          course_code: testCompletedCode,
          grade: testGrade,
          credits: 4.0,
          is_in_progress: isTestInProgress,
        },
      ],
      total_credits: Number(testCredits),
      cumulative_gpa: Number(testCgpa),
    };

    try {
      const res = await curriculumApi.testRuleHarness(currentAst, contextPayload);
      setHarnessResult(res);
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Simulation failed';
      setSimError(errorMsg);
    } finally {
      setIsSimulating(false);
    }
  };

  const handleSave = () => {
    if (onSaveRule) {
      onSaveRule(currentAst, ruleDescription);
    }
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="rule-builder-title"
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.75)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '1.5rem',
      }}
    >
      <div
        style={{
          backgroundColor: '#FFFFFF',
          borderRadius: '12px',
          width: '100%',
          maxWidth: '820px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
          border: '1px solid #E2E8F0',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '1.25rem 1.75rem',
            borderBottom: '1px solid #E2E8F0',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            backgroundColor: '#F8FAFC',
          }}
        >
          <div>
            <h2 id="rule-builder-title" style={{ margin: 0, fontSize: '1.25rem', color: '#0F172A', fontWeight: 600 }}>
              Prerequisite Rule Builder &amp; Test Harness
            </h2>
            <p style={{ margin: '0.25rem 0 0', fontSize: '0.85rem', color: '#64748B' }}>
              Author deterministic prerequisite rules and evaluate them using the pure-Python rule engine.
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            style={{
              background: 'none',
              border: 'none',
              fontSize: '1.5rem',
              cursor: 'pointer',
              color: '#64748B',
              lineHeight: 1,
            }}
          >
            &times;
          </button>
        </div>

        {/* Tab Navigation */}
        <div style={{ display: 'flex', borderBottom: '1px solid #E2E8F0', padding: '0 1.75rem' }}>
          <button
            onClick={() => setActiveTab('builder')}
            style={{
              padding: '0.75rem 1.25rem',
              border: 'none',
              borderBottom: activeTab === 'builder' ? '2px solid #2563EB' : '2px solid transparent',
              background: 'none',
              fontWeight: activeTab === 'builder' ? 600 : 500,
              color: activeTab === 'builder' ? '#2563EB' : '#64748B',
              cursor: 'pointer',
            }}
          >
            1. Visual Rule Authoring
          </button>
          <button
            onClick={() => setActiveTab('harness')}
            style={{
              padding: '0.75rem 1.25rem',
              border: 'none',
              borderBottom: activeTab === 'harness' ? '2px solid #2563EB' : '2px solid transparent',
              background: 'none',
              fontWeight: activeTab === 'harness' ? 600 : 500,
              color: activeTab === 'harness' ? '#2563EB' : '#64748B',
              cursor: 'pointer',
            }}
          >
            2. Interactive Test Harness
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ padding: '1.5rem 1.75rem', overflowY: 'auto', flex: 1 }}>
          {activeTab === 'builder' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: '#334155', marginBottom: '0.4rem' }}>
                  Rule Type (Operator)
                </label>
                <select
                  value={operator}
                  onChange={(e) => setOperator(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.6rem 0.75rem',
                    borderRadius: '6px',
                    border: '1px solid #CBD5E1',
                    marginBottom: '1rem',
                  }}
                >
                  <option value="course_completed">Course Completed (Single)</option>
                  <option value="all_of">Conjunction (All Of - Multiple Courses)</option>
                  <option value="credits_completed">Cumulative Credits Completed</option>
                  <option value="cgpa_min">Minimum CGPA Threshold</option>
                  <option value="corequisite">Concurrent Co-requisite</option>
                  <option value="anti_requisite">Anti-Requisite (Mutual Exclusion)</option>
                </select>

                {(operator === 'course_completed' || operator === 'all_of' || operator === 'corequisite' || operator === 'anti_requisite') && (
                  <>
                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: '#334155', marginBottom: '0.4rem' }}>
                      Target Course Code
                    </label>
                    <input
                      type="text"
                      value={targetCourse}
                      onChange={(e) => setTargetCourse(e.target.value.toUpperCase())}
                      placeholder="e.g. CS-101"
                      style={{
                        width: '100%',
                        padding: '0.6rem 0.75rem',
                        borderRadius: '6px',
                        border: '1px solid #CBD5E1',
                        marginBottom: '1rem',
                      }}
                    />

                    {(operator === 'course_completed' || operator === 'all_of') && (
                      <>
                        <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: '#334155', marginBottom: '0.4rem' }}>
                          Minimum Grade Threshold
                        </label>
                        <select
                          value={minGrade}
                          onChange={(e) => setMinGrade(e.target.value)}
                          style={{
                            width: '100%',
                            padding: '0.6rem 0.75rem',
                            borderRadius: '6px',
                            border: '1px solid #CBD5E1',
                            marginBottom: '1rem',
                          }}
                        >
                          {['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D'].map((g) => (
                            <option key={g} value={g}>
                              Grade {g} or Higher
                            </option>
                          ))}
                        </select>
                      </>
                    )}
                  </>
                )}

                {operator === 'all_of' && (
                  <div style={{ padding: '0.75rem', backgroundColor: '#F1F5F9', borderRadius: '6px', marginBottom: '1rem' }}>
                    <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 600, color: '#334155', marginBottom: '0.4rem' }}>
                      Secondary Course (Conjunctive)
                    </label>
                    <input
                      type="text"
                      value={secondaryCourse}
                      onChange={(e) => setSecondaryCourse(e.target.value.toUpperCase())}
                      placeholder="e.g. MATH-151"
                      style={{
                        width: '100%',
                        padding: '0.5rem 0.75rem',
                        borderRadius: '6px',
                        border: '1px solid #CBD5E1',
                        marginBottom: '0.5rem',
                      }}
                    />
                    <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 600, color: '#334155', marginBottom: '0.4rem' }}>
                      Secondary Grade Threshold
                    </label>
                    <select
                      value={secondaryGrade}
                      onChange={(e) => setSecondaryGrade(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '0.5rem 0.75rem',
                        borderRadius: '6px',
                        border: '1px solid #CBD5E1',
                      }}
                    >
                      {['A', 'B', 'C', 'D'].map((g) => (
                        <option key={g} value={g}>Grade {g}</option>
                      ))}
                    </select>
                  </div>
                )}

                {operator === 'credits_completed' && (
                  <>
                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: '#334155', marginBottom: '0.4rem' }}>
                      Minimum Credits Threshold
                    </label>
                    <input
                      type="number"
                      value={minCredits}
                      onChange={(e) => setMinCredits(Number(e.target.value))}
                      style={{
                        width: '100%',
                        padding: '0.6rem 0.75rem',
                        borderRadius: '6px',
                        border: '1px solid #CBD5E1',
                        marginBottom: '1rem',
                      }}
                    />
                  </>
                )}

                {operator === 'cgpa_min' && (
                  <>
                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: '#334155', marginBottom: '0.4rem' }}>
                      Minimum CGPA Threshold (0.00 – 10.00 Scale)
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      min="0.0"
                      max="10.0"
                      value={minCgpa}
                      onChange={(e) => setMinCgpa(Number(e.target.value))}
                      style={{
                        width: '100%',
                        padding: '0.6rem 0.75rem',
                        borderRadius: '6px',
                        border: '1px solid #CBD5E1',
                        marginBottom: '1rem',
                      }}
                    />
                  </>
                )}

                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: '#334155', marginBottom: '0.4rem' }}>
                  Rule Note / Description
                </label>
                <input
                  type="text"
                  value={ruleDescription}
                  onChange={(e) => setRuleDescription(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.6rem 0.75rem',
                    borderRadius: '6px',
                    border: '1px solid #CBD5E1',
                  }}
                />
              </div>

              {/* JSON Preview Panel */}
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: '#334155', marginBottom: '0.4rem' }}>
                  Generated AST (Grammar v1 Strict JSON)
                </label>
                <pre
                  style={{
                    backgroundColor: '#0F172A',
                    color: '#38BDF8',
                    padding: '1rem',
                    borderRadius: '8px',
                    fontSize: '0.8rem',
                    fontFamily: 'monospace',
                    height: '270px',
                    overflow: 'auto',
                    margin: 0,
                  }}
                >
                  {JSON.stringify(currentAst, null, 2)}
                </pre>
                <div style={{ marginTop: '0.75rem', fontSize: '0.8rem', color: '#64748B' }}>
                  &#10003; Compliant with Schema Version 1, max depth 8, pure-Python AST validator.
                </div>
              </div>
            </div>
          )}

          {activeTab === 'harness' && (
            <div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
                <div>
                  <h4 style={{ margin: '0 0 0.75rem', color: '#1E293B', fontSize: '0.95rem' }}>
                    Hypothetical Student Context
                  </h4>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '0.75rem' }}>
                    <div>
                      <label style={{ fontSize: '0.75rem', color: '#64748B', display: 'block' }}>Student ID</label>
                      <input
                        type="text"
                        value={testStudentId}
                        onChange={(e) => setTestStudentId(e.target.value)}
                        style={{ width: '100%', padding: '0.4rem 0.6rem', border: '1px solid #CBD5E1', borderRadius: '4px' }}
                      />
                    </div>
                    <div>
                      <label style={{ fontSize: '0.75rem', color: '#64748B', display: 'block' }}>Course Taken</label>
                      <input
                        type="text"
                        value={testCompletedCode}
                        onChange={(e) => setTestCompletedCode(e.target.value.toUpperCase())}
                        style={{ width: '100%', padding: '0.4rem 0.6rem', border: '1px solid #CBD5E1', borderRadius: '4px' }}
                      />
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem', marginBottom: '0.75rem' }}>
                    <div>
                      <label style={{ fontSize: '0.75rem', color: '#64748B', display: 'block' }}>Grade</label>
                      <select
                        value={testGrade}
                        onChange={(e) => setTestGrade(e.target.value)}
                        style={{ width: '100%', padding: '0.4rem 0.6rem', border: '1px solid #CBD5E1', borderRadius: '4px' }}
                      >
                        {['A', 'B', 'C', 'D', 'F'].map((g) => (
                          <option key={g} value={g}>{g}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label style={{ fontSize: '0.75rem', color: '#64748B', display: 'block' }}>Total Credits</label>
                      <input
                        type="number"
                        value={testCredits}
                        onChange={(e) => setTestCredits(Number(e.target.value))}
                        style={{ width: '100%', padding: '0.4rem 0.6rem', border: '1px solid #CBD5E1', borderRadius: '4px' }}
                      />
                    </div>
                    <div>
                      <label style={{ fontSize: '0.75rem', color: '#64748B', display: 'block' }}>CGPA</label>
                      <input
                        type="number"
                        step="0.1"
                        value={testCgpa}
                        onChange={(e) => setTestCgpa(Number(e.target.value))}
                        style={{ width: '100%', padding: '0.4rem 0.6rem', border: '1px solid #CBD5E1', borderRadius: '4px' }}
                      />
                    </div>
                  </div>

                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', color: '#475569', marginTop: '0.5rem' }}>
                    <input
                      type="checkbox"
                      checked={isTestInProgress}
                      onChange={(e) => setIsTestInProgress(e.target.checked)}
                    />
                    Mark Course as In-Progress (Tests Kleene INDETERMINATE logic)
                  </label>

                  <button
                    onClick={handleSimulate}
                    disabled={isSimulating}
                    style={{
                      marginTop: '1rem',
                      width: '100%',
                      padding: '0.6rem 1rem',
                      backgroundColor: '#2563EB',
                      color: '#FFFFFF',
                      border: 'none',
                      borderRadius: '6px',
                      fontWeight: 600,
                      cursor: isSimulating ? 'not-allowed' : 'pointer',
                    }}
                  >
                    {isSimulating ? 'Simulating in Pure-Python Engine...' : 'Run Simulation via Test Harness'}
                  </button>
                </div>

                {/* Simulation Output */}
                <div>
                  <h4 style={{ margin: '0 0 0.75rem', color: '#1E293B', fontSize: '0.95rem' }}>
                    Engine Evaluation Result
                  </h4>
                  {simError && (
                    <div style={{ padding: '0.75rem', backgroundColor: '#FEE2E2', color: '#991B1B', borderRadius: '6px', fontSize: '0.85rem' }}>
                      Error: {simError}
                    </div>
                  )}

                  {!harnessResult && !simError && (
                    <div style={{ padding: '2rem', textAlign: 'center', backgroundColor: '#F8FAFC', borderRadius: '6px', border: '1px dashed #CBD5E1', color: '#64748B', fontSize: '0.85rem' }}>
                      Click &quot;Run Simulation&quot; to test the rule against the student context.
                    </div>
                  )}

                  {harnessResult && (
                    <div style={{ backgroundColor: '#F8FAFC', padding: '1rem', borderRadius: '8px', border: '1px solid #E2E8F0' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                        <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#334155' }}>Status:</span>
                        <span
                          style={{
                            padding: '0.25rem 0.6rem',
                            borderRadius: '999px',
                            fontSize: '0.75rem',
                            fontWeight: 700,
                            backgroundColor:
                              harnessResult.status === 'SATISFIED'
                                ? '#DCFCE7'
                                : harnessResult.status === 'INDETERMINATE'
                                ? '#FEF3C7'
                                : '#FEE2E2',
                            color:
                              harnessResult.status === 'SATISFIED'
                                ? '#166534'
                                : harnessResult.status === 'INDETERMINATE'
                                ? '#92400E'
                                : '#991B1B',
                          }}
                        >
                          {harnessResult.status}
                        </span>
                      </div>

                      <div style={{ fontSize: '0.8rem', color: '#475569', marginBottom: '0.5rem' }}>
                        <strong>Eligible:</strong> {harnessResult.eligible ? 'Yes' : 'No'}
                      </div>

                      {harnessResult.blocking_reasons.length > 0 && (
                        <div style={{ marginTop: '0.5rem' }}>
                          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#DC2626' }}>Blocking Reasons:</span>
                          <ul style={{ margin: '0.25rem 0 0', paddingLeft: '1.25rem', fontSize: '0.8rem', color: '#DC2626' }}>
                            {harnessResult.blocking_reasons.map((r, i) => (
                              <li key={i}>{r}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      <div style={{ marginTop: '0.75rem', fontSize: '0.75rem', color: '#64748B' }}>
                        Node: <code>{harnessResult.execution_tree.node_path}</code> ({harnessResult.execution_tree.type})
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: '1rem 1.75rem',
            borderTop: '1px solid #E2E8F0',
            backgroundColor: '#F8FAFC',
            display: 'flex',
            justifyContent: 'flex-end',
            gap: '0.75rem',
          }}
        >
          <button
            onClick={onClose}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#FFFFFF',
              border: '1px solid #CBD5E1',
              borderRadius: '6px',
              fontWeight: 500,
              cursor: 'pointer',
              color: '#475569',
            }}
          >
            Cancel
          </button>
          {onSaveRule && (
            <button
              onClick={handleSave}
              style={{
                padding: '0.5rem 1.25rem',
                backgroundColor: '#1E293B',
                border: 'none',
                borderRadius: '6px',
                fontWeight: 600,
                cursor: 'pointer',
                color: '#FFFFFF',
              }}
            >
              Attach Rule to Curriculum
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
