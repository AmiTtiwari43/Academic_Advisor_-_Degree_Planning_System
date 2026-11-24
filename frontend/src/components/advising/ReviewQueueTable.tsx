import React from 'react';
import { ReviewQueueItem } from '../../api/advising';
import { Badge } from '../Badge/Badge';
import styles from './ReviewQueueTable.module.css';

interface ReviewQueueTableProps {
  queue: ReviewQueueItem[];
  selectedPlanId: string | null;
  onSelectPlan: (planId: string) => void;
  statusFilter: string;
  onStatusFilterChange: (status: string) => void;
  searchQuery: string;
  onSearchQueryChange: (query: string) => void;
  isLoading?: boolean;
}

const STATUS_FILTERS = [
  { label: 'All Plans', value: 'ALL' },
  { label: 'Submitted', value: 'SUBMITTED' },
  { label: 'Under Review', value: 'UNDER_REVIEW' },
  { label: 'Returned', value: 'RETURNED' },
  { label: 'Approved', value: 'APPROVED' },
  { label: 'Rejected', value: 'REJECTED' },
];

export const ReviewQueueTable: React.FC<ReviewQueueTableProps> = ({
  queue,
  selectedPlanId,
  onSelectPlan,
  statusFilter,
  onStatusFilterChange,
  searchQuery,
  onSearchQueryChange,
  isLoading,
}) => {
  const getStatusBadgeVariant = (
    status: string
  ): 'neutral' | 'success' | 'warning' | 'danger' | 'info' => {
    switch (status) {
      case 'APPROVED':
        return 'success';
      case 'SUBMITTED':
      case 'RESUBMITTED':
        return 'info';
      case 'UNDER_REVIEW':
        return 'warning';
      case 'RETURNED':
        return 'warning';
      case 'REJECTED':
        return 'danger';
      default:
        return 'neutral';
    }
  };

  const filteredQueue = queue.filter((item) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const regNo = (item.student_registration_number || `STU-2026-${item.student_id}`).toLowerCase();
    const sName = (item.student_name || '').toLowerCase();
    return (
      regNo.includes(q) ||
      sName.includes(q) ||
      item.student_username.toLowerCase().includes(q) ||
      item.student_email.toLowerCase().includes(q) ||
      item.programme_name.toLowerCase().includes(q) ||
      item.programme_code.toLowerCase().includes(q) ||
      item.plan_name.toLowerCase().includes(q)
    );
  });

  return (
    <div className={styles.container}>
      <div className={styles.filterBar}>
        <div className={styles.filterGroup}>
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.value}
              className={`${styles.pillButton} ${
                statusFilter === f.value ? styles.pillButtonActive : ''
              }`}
              onClick={() => onStatusFilterChange(f.value)}
            >
              {f.label}
            </button>
          ))}
        </div>

        <input
          type="text"
          placeholder="Filter by Registration No, student name, programme, plan..."
          className={styles.searchInput}
          value={searchQuery}
          onChange={(e) => onSearchQueryChange(e.target.value)}
        />
      </div>

      <div className={styles.tableWrapper}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Advisee (Reg No)</th>
              <th>Programme</th>
              <th>Plan & Version</th>
              <th>Status</th>
              <th>Wait Time</th>
              <th>Validation / Risk</th>
              <th>Overrides</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={8} className={styles.emptyState}>
                  Loading advisee queue...
                </td>
              </tr>
            ) : filteredQueue.length === 0 ? (
              <tr>
                <td colSpan={8} className={styles.emptyState}>
                  No degree plans match the current filters.
                </td>
              </tr>
            ) : (
              filteredQueue.map((item) => {
                const isSelected = item.plan_id === selectedPlanId;
                const isAging = item.waiting_days >= 3;
                return (
                  <tr
                    key={item.plan_id}
                    className={`${styles.row} ${isSelected ? styles.selectedRow : ''}`}
                  >
                    <td>
                      <div className={styles.studentInfo}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                          <span className={styles.studentName}>
                            {item.student_name || item.student_username}
                          </span>
                          <span style={{
                            padding: '1px 6px',
                            background: 'rgba(14, 117, 119, 0.1)',
                            color: '#0E7577',
                            fontSize: '11px',
                            fontWeight: 700,
                            borderRadius: '4px',
                          }}>
                            {item.student_registration_number || `STU-2026-${item.student_id}`}
                          </span>
                        </div>
                        <span className={styles.studentMeta}>
                          @{item.student_username} &bull; {item.student_email}
                        </span>
                      </div>
                    </td>
                    <td>
                      <div>
                        <strong>{item.programme_code}</strong>
                        <div className={styles.studentMeta}>{item.programme_name}</div>
                      </div>
                    </td>
                    <td>
                      <div>
                        <span>{item.plan_name}</span>
                        <div className={styles.studentMeta}>v{item.latest_version_number}</div>
                      </div>
                    </td>
                    <td>
                      <Badge variant={getStatusBadgeVariant(item.status)}>{item.status}</Badge>
                    </td>
                    <td>
                      <span
                        className={`${styles.waitBadge} ${
                          isAging ? styles.waitUrgent : styles.waitNormal
                        }`}
                      >
                        {item.waiting_days} {item.waiting_days === 1 ? 'day' : 'days'}
                      </span>
                    </td>
                    <td>
                      {item.hard_constraints_count > 0 ? (
                        <Badge variant="danger">
                          {item.hard_constraints_count} Hard Issue
                          {item.hard_constraints_count > 1 ? 's' : ''}
                        </Badge>
                      ) : item.warnings_count > 0 ? (
                        <Badge variant="warning">{item.warnings_count} Warning(s)</Badge>
                      ) : (
                        <Badge variant="success">Simulation Clean</Badge>
                      )}
                    </td>
                    <td>
                      {item.override_count > 0 ? (
                        <Badge variant="info">{item.override_count} Override(s)</Badge>
                      ) : (
                        <span className={styles.studentMeta}>None</span>
                      )}
                    </td>
                    <td>
                      <button
                        className={styles.actionBtn}
                        onClick={() => onSelectPlan(item.plan_id)}
                      >
                        {isSelected ? 'Reviewing' : 'Review Plan'}
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
