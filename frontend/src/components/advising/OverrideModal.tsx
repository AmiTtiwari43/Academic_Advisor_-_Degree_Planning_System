import React, { useState } from 'react';
import { OverrideType } from '../../api/advising';
import styles from './OverrideModal.module.css';

interface OverrideModalProps {
  isOpen: boolean;
  planName: string;
  versionNumber: number;
  onClose: () => void;
  onConfirm: (data: { override_type: OverrideType; justification: string }) => void;
  isLoading: boolean;
}

const OVERRIDE_OPTIONS: Array<{ label: string; value: OverrideType }> = [
  { label: 'Prerequisite Requirement Override', value: 'PREREQUISITE_OVERRIDE' },
  { label: 'Term Credit Ceiling Override', value: 'CREDIT_CEILING_OVERRIDE' },
  { label: 'Course Offering Schedule Override', value: 'OFFERING_OVERRIDE' },
  { label: 'General Degree Requirement Override', value: 'GENERAL_OVERRIDE' },
];

export const OverrideModal: React.FC<OverrideModalProps> = ({
  isOpen,
  planName,
  versionNumber,
  onClose,
  onConfirm,
  isLoading,
}) => {
  const [overrideType, setOverrideType] = useState<OverrideType>('PREREQUISITE_OVERRIDE');
  const [justification, setJustification] = useState('');

  if (!isOpen) return null;

  const charCount = justification.trim().length;
  const isJustificationValid = charCount >= 15;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isJustificationValid || isLoading) return;
    onConfirm({ override_type: overrideType, justification: justification.trim() });
  };

  return (
    <div className={styles.overlay} role="dialog" aria-modal="true">
      <div className={styles.modal}>
        <div className={styles.header}>
          <h3 className={styles.title}>Record Academic Override</h3>
          <button className={styles.closeBtn} onClick={onClose} disabled={isLoading}>
            &times;
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className={styles.body}>
            <div className={styles.warningBanner}>
              <strong>Authoritative Override Warning:</strong> Overrides are permanent and
              strictly immutable once recorded. Overrides apply strictly to degree planning
              simulations and <em>never mutate official student transcript records</em>.
            </div>

            <div className={styles.fieldGroup}>
              <label className={styles.label}>Target Plan:</label>
              <span>
                {planName} &bull; Version {versionNumber}
              </span>
            </div>

            <div className={styles.fieldGroup}>
              <label className={styles.label}>Override Category:</label>
              <select
                className={styles.select}
                value={overrideType}
                onChange={(e) => setOverrideType(e.target.value as OverrideType)}
              >
                {OVERRIDE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div className={styles.fieldGroup}>
              <label className={styles.label}>Academic Justification (Required):</label>
              <textarea
                className={styles.textarea}
                value={justification}
                onChange={(e) => setJustification(e.target.value)}
                placeholder="State the verifiable academic rationale, transfer credit equivalency, or department chair approval for this override (minimum 15 characters)..."
                rows={4}
                required
              />
              <div className={styles.charCounter}>
                <span>Minimum 15 characters required</span>
                <span className={isJustificationValid ? styles.counterValid : styles.counterInvalid}>
                  {charCount} / 15 chars
                </span>
              </div>
            </div>
          </div>

          <div className={styles.footer}>
            <button
              type="button"
              className={styles.btnCancel}
              onClick={onClose}
              disabled={isLoading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className={styles.btnSubmit}
              disabled={!isJustificationValid || isLoading}
            >
              {isLoading ? 'Recording Override...' : 'Record Authoritative Override'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
