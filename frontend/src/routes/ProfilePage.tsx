import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  User as UserIcon,
  GraduationCap,
  CheckCircle2,
  AlertCircle,
  Save,
  Shield,
  Building2,
} from 'lucide-react';
import { authApi } from '../api/auth';
import { useAuth } from '../context/AuthContext';
import { Badge } from '../components/Badge/Badge';
import { PageHeader } from '../components/PageHeader/PageHeader';
import { UserProfileData } from '../types';
import styles from './ProfilePage.module.css';

export const ProfilePage: React.FC = () => {
  const { user, activeRole, refreshUser } = useAuth();
  const queryClient = useQueryClient();

  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [preferredName, setPreferredName] = useState('');
  const [email, setEmail] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: profile, isLoading } = useQuery<UserProfileData>({
    queryKey: ['user-profile'],
    queryFn: () => authApi.getProfile(),
    staleTime: 1000 * 60 * 5,
  });

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
  }, [profile, user]);

  const updateMutation = useMutation({
    mutationFn: (data: Partial<UserProfileData>) => authApi.updateProfile(data),
    onSuccess: async () => {
      setSuccessMessage('Your profile changes have been saved successfully.');
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

  const academicSummary = profile?.academic_summary;

  return (
    <div className={styles.container}>
      <PageHeader
        title="User Profile & Settings"
        subtitle="Manage your personal information, review institutional standing, and configure profile details."
      />

      <div className={styles.profileCard}>
        {/* Banner */}
        <div className={styles.headerBanner}>
          <div className={styles.headerLeft}>
            <div className={styles.avatarLarge}>{userInitials}</div>
            <div className={styles.headerDetails}>
              <div className={styles.nameRow}>
                <h2 className={styles.fullName}>{displayName}</h2>
                <Badge variant="teal" size="sm">
                  {activeRole ? activeRole.replace('_', ' ') : 'Academic Portal'}
                </Badge>
              </div>
              <span className={styles.username}>@{profile?.username || user?.username}</span>
              <div className={styles.instTag}>
                <Building2 size={14} />
                <span>{profile?.institution_name || 'Metropolitan State University'}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSave} className={styles.cardBody}>
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

          {/* Academic Info for Students */}
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
                <label htmlFor="p-first-name" className={styles.label}>
                  First Name
                </label>
                <input
                  id="p-first-name"
                  type="text"
                  className={styles.input}
                  value={firstName}
                  onChange={(e) => handleFirstNameChange(e.target.value)}
                  placeholder="First name"
                  disabled={isLoading || updateMutation.isPending}
                />
              </div>

              <div className={styles.formGroup}>
                <label htmlFor="p-last-name" className={styles.label}>
                  Last Name
                </label>
                <input
                  id="p-last-name"
                  type="text"
                  className={styles.input}
                  value={lastName}
                  onChange={(e) => handleLastNameChange(e.target.value)}
                  placeholder="Last name"
                  disabled={isLoading || updateMutation.isPending}
                />
              </div>

              <div className={`${styles.formGroup} ${styles.inputFull}`}>
                <label htmlFor="p-pref-name" className={styles.label}>
                  Preferred Name (Displays across dashboard, headers & advising)
                </label>
                <input
                  id="p-pref-name"
                  type="text"
                  className={styles.input}
                  value={preferredName}
                  onChange={(e) => setPreferredName(e.target.value)}
                  placeholder="e.g. Alex (optional; automatically syncs with First & Last name)"
                  disabled={isLoading || updateMutation.isPending}
                />
              </div>

              <div className={styles.formGroup}>
                <label htmlFor="p-email" className={styles.label}>
                  Institutional Email
                </label>
                <input
                  id="p-email"
                  type="email"
                  className={styles.input}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="student@university.edu"
                  disabled={isLoading || updateMutation.isPending}
                />
              </div>

              <div className={styles.formGroup}>
                <label htmlFor="p-phone" className={styles.label}>
                  Phone Number
                </label>
                <input
                  id="p-phone"
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

          {/* Account Security Info */}
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
                  {activeRole ? activeRole.replace('_', ' ') : 'Student'}
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

          {/* Action Row */}
          <div className={styles.actionsRow}>
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
