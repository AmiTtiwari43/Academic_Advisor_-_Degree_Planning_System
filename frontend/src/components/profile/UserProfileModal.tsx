import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  X,
  User as UserIcon,
  GraduationCap,
  CheckCircle2,
  AlertCircle,
  Save,
  Shield,
  Building2,
} from 'lucide-react';
import { authApi } from '../../api/auth';
import { useAuth } from '../../context/AuthContext';
import { Badge } from '../Badge/Badge';
import { UserProfileData } from '../../types';
import styles from './UserProfileModal.module.css';

export interface UserProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const UserProfileModal: React.FC<UserProfileModalProps> = ({ isOpen, onClose }) => {
  const { user, activeRole, roleDisplayName, refreshUser } = useAuth();
  const queryClient = useQueryClient();

  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [preferredName, setPreferredName] = useState('');
  const [email, setEmail] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Fetch complete profile metadata
  const { data: profile, isLoading } = useQuery<UserProfileData>({
    queryKey: ['user-profile'],
    queryFn: () => authApi.getProfile(),
    enabled: isOpen,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });

  // Synchronize form state when profile data arrives
  useEffect(() => {
    if (profile) {
      setFirstName(profile.first_name || user?.first_name || '');
      setLastName(profile.last_name || user?.last_name || '');
      setPreferredName(profile.preferred_name || user?.preferred_name || '');
      setEmail(profile.email || user?.email || '');
      setPhoneNumber(profile.phone_number || user?.phone_number || '');
    } else if (user) {
      setFirstName(user.first_name || '');
      setLastName(user.last_name || '');
      setPreferredName(user.preferred_name || '');
      setEmail(user.email || '');
      setPhoneNumber(user.phone_number || '');
    }
  }, [profile, user, isOpen]);

  // Clear messages on modal open
  useEffect(() => {
    if (isOpen) {
      setSuccessMessage(null);
      setErrorMessage(null);
    }
  }, [isOpen]);

  // Close on Escape key
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Mutation to update profile
  const updateMutation = useMutation({
    mutationFn: (data: Partial<UserProfileData>) => authApi.updateProfile(data),
    onSuccess: async () => {
      setSuccessMessage('Profile information successfully updated.');
      setErrorMessage(null);
      await queryClient.invalidateQueries();
      await refreshUser();
    },
    onError: (err: unknown) => {
      const axiosErr = err as { response?: { data?: { detail?: string; error?: string } } };
      setErrorMessage(
        axiosErr?.response?.data?.detail ||
        axiosErr?.response?.data?.error ||
        'Failed to save profile changes. Please try again.'
      );
      setSuccessMessage(null);
    },
  });

  if (!isOpen) return null;

  const handleFirstNameChange = (val: string) => {
    const oldFull = `${firstName} ${lastName}`.trim();
    setFirstName(val);
    if (!preferredName || preferredName === oldFull || preferredName === firstName) {
      setPreferredName(`${val} ${lastName}`.trim());
    }
  };

  const handleLastNameChange = (val: string) => {
    const oldFull = `${firstName} ${lastName}`.trim();
    setLastName(val);
    if (!preferredName || preferredName === oldFull || preferredName === lastName) {
      setPreferredName(`${firstName} ${val}`.trim());
    }
  };

  const displayName = preferredName?.trim() || (firstName ? `${firstName} ${lastName}`.trim() : user?.username) || 'User';

  const userInitials = preferredName?.trim()
    ? preferredName
        .trim()
        .split(/\s+/)
        .map((p) => p[0])
        .join('')
        .slice(0, 2)
        .toUpperCase()
    : firstName
    ? `${firstName[0]}${lastName ? lastName[0] : ''}`.toUpperCase()
    : (user?.username ? user.username.slice(0, 2).toUpperCase() : 'AU');

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSuccessMessage(null);
    setErrorMessage(null);

    updateMutation.mutate({
      first_name: firstName.trim(),
      last_name: lastName.trim(),
      preferred_name: preferredName.trim(),
      email: email.trim(),
      phone_number: phoneNumber.trim(),
    });
  };

  const academicSummary = profile?.academic_summary;

  return (
    <div
      className={styles.backdrop}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="user-profile-title"
    >
      <div className={styles.modal}>
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.headerUserBlock}>
            <div className={styles.avatarLarge}>{userInitials}</div>
            <div className={styles.headerMeta}>
              <div className={styles.nameRow}>
                <h2 id="user-profile-title" className={styles.fullName}>
                  {displayName}
                </h2>
                <Badge variant="teal" size="sm">
                  {roleDisplayName || (activeRole ? activeRole.replace('_', ' ') : 'Student')}
                </Badge>
                {(profile?.registration_number || user?.registration_number) && (
                  <Badge variant="neutral" size="sm">
                    REG: {profile?.registration_number || user?.registration_number}
                  </Badge>
                )}
              </div>
              <span className={styles.username}>@{profile?.username || user?.username}</span>
              <div className={styles.institutionRow}>
                <Building2 size={13} />
                <span>{profile?.institution_name || 'Metropolitan State University'}</span>
              </div>
            </div>
          </div>
          <button
            type="button"
            className={styles.closeButton}
            onClick={onClose}
            aria-label="Close profile window"
          >
            <X size={18} />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSave} className={styles.body}>
          {successMessage && (
            <div className={styles.alertSuccess} role="status">
              <CheckCircle2 size={16} />
              <span>{successMessage}</span>
            </div>
          )}

          {errorMessage && (
            <div className={styles.alertError} role="alert">
              <AlertCircle size={16} />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Academic Info Banner for Students */}
          {academicSummary && academicSummary.programme && (
            <div className={styles.academicCard}>
              <div className={styles.cardTitle}>
                <GraduationCap size={16} />
                <span>Academic Record & Standing (10-Point Scale)</span>
              </div>
              <div className={styles.statsGrid}>
                <div className={styles.statItem}>
                  <span className={styles.statLabel}>Cumulative GPA</span>
                  <span className={styles.statValue}>{academicSummary.cgpa || '0.00 / 10.00'}</span>
                </div>
                <div className={styles.statItem}>
                  <span className={styles.statLabel}>Earned Credits</span>
                  <span className={styles.statValue}>{academicSummary.credits_earned || 0} cr</span>
                </div>
                <div className={styles.statItem}>
                  <span className={styles.statLabel}>Standing</span>
                  <span className={styles.statValue}>{academicSummary.status || 'Active'}</span>
                </div>
              </div>
              <div className={styles.detailsList}>
                <div className={styles.detailRow}>
                  <span className={styles.detailKey}>Degree Programme</span>
                  <span className={styles.detailVal}>
                    {academicSummary.programme} ({academicSummary.programme_code})
                  </span>
                </div>
                <div className={styles.detailRow}>
                  <span className={styles.detailKey}>Assigned Faculty Advisor</span>
                  <span className={styles.detailVal}>{academicSummary.advisor || 'Not Assigned'}</span>
                </div>
                <div className={styles.detailRow}>
                  <span className={styles.detailKey}>Enrollment Term</span>
                  <span className={styles.detailVal}>{academicSummary.enrollment_term || 'Fall 2024'}</span>
                </div>
                <div className={styles.detailRow}>
                  <span className={styles.detailKey}>Evaluation Scale</span>
                  <span className={styles.detailVal}>Standardized 1.00 – 10.00 Scale</span>
                </div>
              </div>
            </div>
          )}

          {/* Personal Information (Editable) */}
          <div className={styles.formSection}>
            <div className={styles.sectionHeader}>
              <div className={styles.sectionTitle}>
                <UserIcon size={16} />
                <span>Personal & Contact Information</span>
              </div>
              <span className={styles.helpText}>Editable by user</span>
            </div>

            <div className={styles.inputGrid}>
              <div className={styles.formGroup}>
                <label htmlFor="prof-first-name" className={styles.label}>
                  First Name
                </label>
                <input
                  id="prof-first-name"
                  type="text"
                  className={styles.input}
                  value={firstName}
                  onChange={(e) => handleFirstNameChange(e.target.value)}
                  placeholder="First name"
                  disabled={isLoading || updateMutation.isPending}
                />
              </div>

              <div className={styles.formGroup}>
                <label htmlFor="prof-last-name" className={styles.label}>
                  Last Name
                </label>
                <input
                  id="prof-last-name"
                  type="text"
                  className={styles.input}
                  value={lastName}
                  onChange={(e) => handleLastNameChange(e.target.value)}
                  placeholder="Last name"
                  disabled={isLoading || updateMutation.isPending}
                />
              </div>

              <div className={`${styles.formGroup} ${styles.inputFull}`}>
                <label htmlFor="prof-pref-name" className={styles.label}>
                  Preferred Name (Displays across dashboard, headers & advising)
                </label>
                <input
                  id="prof-pref-name"
                  type="text"
                  className={styles.input}
                  value={preferredName}
                  onChange={(e) => setPreferredName(e.target.value)}
                  placeholder="e.g. Alex (optional; automatically syncs with First & Last name)"
                  disabled={isLoading || updateMutation.isPending}
                />
              </div>

              <div className={styles.formGroup}>
                <label htmlFor="prof-email" className={styles.label}>
                  Institutional Email
                </label>
                <input
                  id="prof-email"
                  type="email"
                  className={styles.input}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="student@university.edu"
                  disabled={isLoading || updateMutation.isPending}
                />
              </div>

              <div className={styles.formGroup}>
                <label htmlFor="prof-phone" className={styles.label}>
                  Phone Number
                </label>
                <input
                  id="prof-phone"
                  type="tel"
                  className={styles.input}
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder="+1 (555) 000-0000"
                  disabled={isLoading || updateMutation.isPending}
                />
              </div>
            </div>
          </div>

          {/* Account & Security Summary */}
          <div className={styles.formSection}>
            <div className={styles.sectionHeader}>
              <div className={styles.sectionTitle}>
                <Shield size={16} />
                <span>Account Security & Authorization</span>
              </div>
            </div>
            <div className={styles.detailsList}>
              <div className={styles.detailRow}>
                <span className={styles.detailKey}>Institutional Role</span>
                <span className={styles.detailVal}>
                  {roleDisplayName || (activeRole ? activeRole.replace('_', ' ') : 'Student')}
                </span>
              </div>
              <div className={styles.detailRow}>
                <span className={styles.detailKey}>Account Status</span>
                <span className={styles.detailVal}>Active & Verified</span>
              </div>
              <div className={styles.detailRow}>
                <span className={styles.detailKey}>Security Permissions</span>
                <span className={styles.detailVal}>
                  {user?.is_superuser ? 'Full System Administrator' : 'Role-Scoped Authorization'}
                </span>
              </div>
              <div className={styles.detailRow}>
                <span className={styles.detailKey}>Multi-Factor / Session</span>
                <span className={styles.detailVal}>Authenticated Institutional Session</span>
              </div>
            </div>
          </div>

          {/* Footer Actions */}
          <div className={styles.footer}>
            <button
              type="button"
              className={styles.btnCancel}
              onClick={onClose}
              disabled={updateMutation.isPending}
            >
              Cancel
            </button>
            <button
              type="submit"
              className={styles.btnSave}
              disabled={updateMutation.isPending || isLoading}
            >
              {updateMutation.isPending ? (
                <>
                  <div className={styles.spinner} />
                  <span>Saving Changes...</span>
                </>
              ) : (
                <>
                  <Save size={15} />
                  <span>Save Profile Changes</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
