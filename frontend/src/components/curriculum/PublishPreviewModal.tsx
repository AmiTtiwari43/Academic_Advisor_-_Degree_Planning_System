import React, { useEffect, useState } from 'react';
import { curriculumApi, PublishPreview } from '../../api/curriculum';

interface PublishPreviewModalProps {
  versionId: string;
  isOpen: boolean;
  onClose: () => void;
  onPublishedSuccess: () => void;
}

export const PublishPreviewModal: React.FC<PublishPreviewModalProps> = ({
  versionId,
  isOpen,
  onClose,
  onPublishedSuccess,
}) => {
  const [preview, setPreview] = useState<PublishPreview | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isPublishing, setIsPublishing] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !versionId) return;

    let isMounted = true;
    setIsLoading(true);
    setErrorMsg(null);

    curriculumApi
      .getPublishPreview(versionId)
      .then((data) => {
        if (isMounted) {
          setPreview(data);
          setIsLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          setErrorMsg(err instanceof Error ? err.message : 'Failed to load preview');
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, versionId]);

  if (!isOpen) return null;

  const handleConfirmPublish = async () => {
    setIsPublishing(true);
    setErrorMsg(null);
    try {
      await curriculumApi.publishVersion(versionId);
      onPublishedSuccess();
      onClose();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Publication failed');
      setIsPublishing(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="publish-preview-title"
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
          maxWidth: '640px',
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
            <h2 id="publish-preview-title" style={{ margin: 0, fontSize: '1.25rem', color: '#0F172A', fontWeight: 600 }}>
              Curriculum Publication Preview
            </h2>
            <p style={{ margin: '0.25rem 0 0', fontSize: '0.85rem', color: '#64748B' }}>
              Review the version structure before transitioning to immutable published status.
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
          {isLoading && (
            <div style={{ textAlign: 'center', padding: '2rem', color: '#64748B' }}>
              Loading curriculum validation preview...
            </div>
          )}

          {errorMsg && (
            <div style={{ padding: '0.75rem', backgroundColor: '#FEE2E2', color: '#991B1B', borderRadius: '6px', fontSize: '0.85rem', marginBottom: '1rem' }}>
              {errorMsg}
            </div>
          )}

          {preview && (
            <div>
              {/* Summary Stats Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem', marginBottom: '1.25rem' }}>
                <div style={{ padding: '0.75rem', backgroundColor: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px' }}>
                  <div style={{ fontSize: '0.75rem', color: '#64748B' }}>Programme</div>
                  <div style={{ fontSize: '1rem', fontWeight: 700, color: '#0F172A' }}>{preview.programme_code}</div>
                </div>
                <div style={{ padding: '0.75rem', backgroundColor: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px' }}>
                  <div style={{ fontSize: '0.75rem', color: '#64748B' }}>Version</div>
                  <div style={{ fontSize: '1rem', fontWeight: 700, color: '#0F172A' }}>v{preview.version_number}</div>
                </div>
                <div style={{ padding: '0.75rem', backgroundColor: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px' }}>
                  <div style={{ fontSize: '0.75rem', color: '#64748B' }}>Required Credits</div>
                  <div style={{ fontSize: '1rem', fontWeight: 700, color: '#0F172A' }}>{preview.total_credits_required} cr</div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem', marginBottom: '1.25rem' }}>
                <div style={{ padding: '0.75rem', backgroundColor: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px' }}>
                  <div style={{ fontSize: '0.75rem', color: '#64748B' }}>Requirement Groups</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#0F172A' }}>{preview.total_requirement_groups}</div>
                </div>
                <div style={{ padding: '0.75rem', backgroundColor: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px' }}>
                  <div style={{ fontSize: '0.75rem', color: '#64748B' }}>Unique Courses</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#0F172A' }}>{preview.total_unique_courses}</div>
                </div>
                <div style={{ padding: '0.75rem', backgroundColor: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px' }}>
                  <div style={{ fontSize: '0.75rem', color: '#64748B' }}>Prerequisite Rules</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#0F172A' }}>{preview.total_prerequisite_rules}</div>
                </div>
              </div>

              {/* Validation Status */}
              {preview.validation_report.errors.length > 0 ? (
                <div style={{ padding: '1rem', backgroundColor: '#FEF2F2', border: '1px solid #FCA5A5', borderRadius: '8px', marginBottom: '1rem' }}>
                  <h4 style={{ margin: '0 0 0.5rem', color: '#991B1B', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span>&#9888;</span> Pre-Publication Validation Failed ({preview.validation_report.errors.length} Errors)
                  </h4>
                  <ul style={{ margin: 0, paddingLeft: '1.25rem', color: '#B91C1C', fontSize: '0.8rem' }}>
                    {preview.validation_report.errors.map((e, idx) => (
                      <li key={idx}><strong>{e.code}:</strong> {e.message}</li>
                    ))}
                  </ul>
                  <p style={{ margin: '0.5rem 0 0', fontSize: '0.75rem', color: '#991B1B' }}>
                    Resolve all validation errors before this curriculum version can be published.
                  </p>
                </div>
              ) : (
                <div style={{ padding: '1rem', backgroundColor: '#F0FDF4', border: '1px solid #86EFAC', borderRadius: '8px', marginBottom: '1rem' }}>
                  <h4 style={{ margin: '0 0 0.25rem', color: '#166534', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span>&#10003;</span> All Validation Checks Passed
                  </h4>
                  <p style={{ margin: 0, fontSize: '0.8rem', color: '#15803D' }}>
                    The curriculum is well-formed, acyclic, and consistent. Publishing will freeze this version immutably.
                  </p>
                </div>
              )}

              {preview.validation_report.warnings.length > 0 && (
                <div style={{ padding: '0.75rem 1rem', backgroundColor: '#FFFBEB', border: '1px solid #FCD34D', borderRadius: '8px', marginBottom: '1rem' }}>
                  <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#92400E' }}>Warnings ({preview.validation_report.warnings.length}):</span>
                  <ul style={{ margin: '0.25rem 0 0', paddingLeft: '1.25rem', color: '#B45309', fontSize: '0.75rem' }}>
                    {preview.validation_report.warnings.map((w, idx) => (
                      <li key={idx}>{w.message}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Immutability Notice */}
              <div style={{ padding: '0.75rem', backgroundColor: '#F1F5F9', borderRadius: '6px', fontSize: '0.75rem', color: '#475569' }}>
                <strong>Strict Immutability Notice:</strong> Once published, this curriculum version and all its child requirement groups, courses, and rules cannot be modified or deleted. Any future revisions require cloning to a new draft version.
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
            disabled={isPublishing}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#FFFFFF',
              border: '1px solid #CBD5E1',
              borderRadius: '6px',
              fontWeight: 500,
              cursor: isPublishing ? 'not-allowed' : 'pointer',
              color: '#475569',
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleConfirmPublish}
            disabled={!preview?.can_publish || isPublishing}
            style={{
              padding: '0.5rem 1.25rem',
              backgroundColor: preview?.can_publish ? '#166534' : '#94A3B8',
              border: 'none',
              borderRadius: '6px',
              fontWeight: 600,
              cursor: preview?.can_publish && !isPublishing ? 'pointer' : 'not-allowed',
              color: '#FFFFFF',
            }}
          >
            {isPublishing ? 'Publishing...' : 'Confirm & Publish Curriculum'}
          </button>
        </div>
      </div>
    </div>
  );
};
