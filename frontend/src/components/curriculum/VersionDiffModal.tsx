import React, { useEffect, useState } from 'react';
import { curriculumApi, CurriculumVersionSummary } from '../../api/curriculum';

interface VersionDiffModalProps {
  currentVersionId: string;
  allVersions: CurriculumVersionSummary[];
  isOpen: boolean;
  onClose: () => void;
}

export const VersionDiffModal: React.FC<VersionDiffModalProps> = ({
  currentVersionId,
  allVersions,
  isOpen,
  onClose,
}) => {
  const otherVersions = allVersions.filter((v) => v.id !== currentVersionId);
  const [selectedOtherId, setSelectedOtherId] = useState<string>(
    otherVersions[0]?.id || ''
  );
  const [diffData, setDiffData] = useState<Record<string, unknown> | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !currentVersionId || !selectedOtherId) return;

    let isMounted = true;
    setIsLoading(true);
    setErrorMsg(null);

    curriculumApi
      .diffVersions(currentVersionId, selectedOtherId)
      .then((data) => {
        if (isMounted) {
          setDiffData(data);
          setIsLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          setErrorMsg(err instanceof Error ? err.message : 'Failed to calculate version diff');
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, currentVersionId, selectedOtherId]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="diff-modal-title"
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
          maxWidth: '720px',
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
            <h2 id="diff-modal-title" style={{ margin: 0, fontSize: '1.25rem', color: '#0F172A', fontWeight: 600 }}>
              Curriculum Version Comparison Diff
            </h2>
            <p style={{ margin: '0.25rem 0 0', fontSize: '0.85rem', color: '#64748B' }}>
              Compare structural changes across published and draft curriculum versions.
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

        {/* Content */}
        <div style={{ padding: '1.5rem 1.75rem', overflowY: 'auto', flex: 1 }}>
          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: '#334155', marginBottom: '0.4rem' }}>
              Compare Current Version With:
            </label>
            <select
              value={selectedOtherId}
              onChange={(e) => setSelectedOtherId(e.target.value)}
              style={{
                width: '100%',
                padding: '0.6rem 0.75rem',
                borderRadius: '6px',
                border: '1px solid #CBD5E1',
                fontSize: '0.9rem',
              }}
            >
              {otherVersions.map((v) => (
                <option key={v.id} value={v.id}>
                  v{v.version_number} ({v.academic_year}) - [{v.status}]
                </option>
              ))}
            </select>
          </div>

          {isLoading && (
            <div style={{ textAlign: 'center', padding: '2rem', color: '#64748B' }}>
              Computing side-by-side diff...
            </div>
          )}

          {errorMsg && (
            <div style={{ padding: '0.75rem', backgroundColor: '#FEE2E2', color: '#991B1B', borderRadius: '6px', fontSize: '0.85rem' }}>
              {errorMsg}
            </div>
          )}

          {diffData && (
            <div>
              {/* Metadata Changes */}
              <div style={{ marginBottom: '1.25rem', backgroundColor: '#F8FAFC', padding: '1rem', borderRadius: '8px', border: '1px solid #E2E8F0' }}>
                <h4 style={{ margin: '0 0 0.5rem', color: '#1E293B', fontSize: '0.9rem' }}>Metadata Comparison</h4>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', fontSize: '0.85rem' }}>
                  <div>
                    <span style={{ color: '#64748B' }}>Current Credits: </span>
                    <strong>{String((diffData.metadata as Record<string, unknown>)?.v1 ? ((diffData.metadata as Record<string, unknown>).v1 as Record<string, unknown>).total_credits_required : '-')} cr</strong>
                  </div>
                  <div>
                    <span style={{ color: '#64748B' }}>Compared Credits: </span>
                    <strong>{String((diffData.metadata as Record<string, unknown>)?.v2 ? ((diffData.metadata as Record<string, unknown>).v2 as Record<string, unknown>).total_credits_required : '-')} cr</strong>
                  </div>
                </div>
              </div>

              {/* Added / Removed Courses */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.25rem' }}>
                <div style={{ padding: '0.75rem', backgroundColor: '#F0FDF4', border: '1px solid #BBF7D0', borderRadius: '8px' }}>
                  <h4 style={{ margin: '0 0 0.5rem', color: '#166534', fontSize: '0.85rem' }}>
                    + Courses Added in Compared Version (
                    {Array.isArray((diffData.courses as Record<string, unknown>)?.added)
                      ? ((diffData.courses as Record<string, unknown>).added as unknown[]).length
                      : 0}
                    )
                  </h4>
                  {Array.isArray((diffData.courses as Record<string, unknown>)?.added) &&
                  ((diffData.courses as Record<string, unknown>).added as unknown[]).length > 0 ? (
                    <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.8rem', color: '#15803D' }}>
                      {((diffData.courses as Record<string, unknown>).added as Array<{ code: string; title: string }>).map((c, i) => (
                        <li key={i}>{c.code} - {c.title}</li>
                      ))}
                    </ul>
                  ) : (
                    <p style={{ margin: 0, fontSize: '0.8rem', color: '#64748B' }}>None</p>
                  )}
                </div>

                <div style={{ padding: '0.75rem', backgroundColor: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '8px' }}>
                  <h4 style={{ margin: '0 0 0.5rem', color: '#991B1B', fontSize: '0.85rem' }}>
                    - Courses Removed in Compared Version (
                    {Array.isArray((diffData.courses as Record<string, unknown>)?.removed)
                      ? ((diffData.courses as Record<string, unknown>).removed as unknown[]).length
                      : 0}
                    )
                  </h4>
                  {Array.isArray((diffData.courses as Record<string, unknown>)?.removed) &&
                  ((diffData.courses as Record<string, unknown>).removed as unknown[]).length > 0 ? (
                    <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.8rem', color: '#B91C1C' }}>
                      {((diffData.courses as Record<string, unknown>).removed as Array<{ code: string; title: string }>).map((c, i) => (
                        <li key={i}>{c.code} - {c.title}</li>
                      ))}
                    </ul>
                  ) : (
                    <p style={{ margin: 0, fontSize: '0.8rem', color: '#64748B' }}>None</p>
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
          }}
        >
          <button
            onClick={onClose}
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
            Close Diff
          </button>
        </div>
      </div>
    </div>
  );
};
