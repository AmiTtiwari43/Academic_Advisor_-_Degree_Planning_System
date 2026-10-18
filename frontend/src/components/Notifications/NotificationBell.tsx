import React, { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Bell, Check, Inbox } from 'lucide-react';
import { notificationsApi, NotificationItem } from '../../api/notifications';
import { Badge } from '../Badge/Badge';
import styles from './NotificationBell.module.css';

function formatRelativeTime(dateString: string): string {
  try {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMinutes = Math.floor(diffMs / 60000);

    if (diffMinutes < 1) return 'Just now';
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return dateString;
  }
}

function getEventBadge(eventType: string) {
  switch (eventType) {
    case 'PLAN_APPROVED':
      return <Badge variant="success" size="sm">Approved</Badge>;
    case 'PLAN_RETURNED':
      return <Badge variant="warning" size="sm">Returned</Badge>;
    case 'PLAN_REJECTED':
      return <Badge variant="danger" size="sm">Rejected</Badge>;
    case 'PREREQUISITE_RISK':
      return <Badge variant="danger" size="sm">Prereq Risk</Badge>;
    case 'PLAN_SUBMITTED':
      return <Badge variant="info" size="sm">Submitted</Badge>;
    case 'PLAN_UNDER_REVIEW':
      return <Badge variant="info" size="sm">Reviewing</Badge>;
    case 'ADVISOR_QUEUE_SUMMARY':
      return <Badge variant="teal" size="sm">Queue</Badge>;
    case 'REGISTRATION_REMINDER':
    default:
      return <Badge variant="neutral" size="sm">Notice</Badge>;
  }
}

export const NotificationBell: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  // Query unread count with 30s background poll
  const { data: countData } = useQuery({
    queryKey: ['notifications-unread-count'],
    queryFn: () => notificationsApi.getUnreadCount(),
    refetchInterval: 30000,
  });

  const unreadCount = countData?.unread_count ?? 0;

  // Query notifications list when dropdown is open
  const { data: notifications, isLoading } = useQuery({
    queryKey: ['notifications', unreadOnly],
    queryFn: () => notificationsApi.listNotifications(unreadOnly),
    enabled: isOpen,
  });

  // Mark single as read mutation
  const markReadMutation = useMutation({
    mutationFn: (id: string) => notificationsApi.markAsRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications-unread-count'] });
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  // Mark all as read mutation
  const markAllReadMutation = useMutation({
    mutationFn: () => notificationsApi.markAllAsRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications-unread-count'] });
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  // Handle outside click & escape key
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  const handleToggle = () => {
    setIsOpen(!isOpen);
  };

  const handleMarkAsRead = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    markReadMutation.mutate(id);
  };

  const handleMarkAllAsRead = () => {
    markAllReadMutation.mutate();
  };

  return (
    <div className={styles.container} ref={dropdownRef}>
      <button
        type="button"
        className={`${styles.bellButton} ${isOpen ? styles.bellButtonActive : ''}`}
        onClick={handleToggle}
        aria-label={`Notifications (${unreadCount} unread)`}
        aria-expanded={isOpen}
        aria-haspopup="true"
        data-testid="notification-bell-btn"
      >
        <Bell size={20} />
        {unreadCount > 0 && (
          <span className={styles.badgeCount} data-testid="notification-badge-count">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className={styles.dropdown} role="dialog" aria-label="Notifications panel">
          <div className={styles.header}>
            <h3 className={styles.title}>
              Notifications
              {unreadCount > 0 && (
                <Badge variant="neutral" size="sm">
                  {unreadCount} new
                </Badge>
              )}
            </h3>
            <div className={styles.actions}>
              <button
                type="button"
                className={styles.markAllBtn}
                onClick={handleMarkAllAsRead}
                disabled={unreadCount === 0 || markAllReadMutation.isPending}
                data-testid="mark-all-read-btn"
              >
                Mark all read
              </button>
            </div>
          </div>

          <div className={styles.filterTabs}>
            <button
              type="button"
              className={`${styles.tabBtn} ${!unreadOnly ? styles.tabBtnActive : ''}`}
              onClick={() => setUnreadOnly(false)}
              data-testid="filter-all-btn"
            >
              All
            </button>
            <button
              type="button"
              className={`${styles.tabBtn} ${unreadOnly ? styles.tabBtnActive : ''}`}
              onClick={() => setUnreadOnly(true)}
              data-testid="filter-unread-btn"
            >
              Unread only
            </button>
          </div>

          <div className={styles.list}>
            {isLoading ? (
              <div className={styles.loadingState}>Loading notifications...</div>
            ) : notifications && notifications.length > 0 ? (
              notifications.map((item: NotificationItem) => (
                <div
                  key={item.id}
                  className={`${styles.item} ${item.read_status === 'UNREAD' ? styles.itemUnread : styles.itemRead}`}
                  data-testid={`notification-item-${item.id}`}
                >
                  <div className={styles.itemTop}>
                    <div className={styles.itemMeta}>
                      {getEventBadge(item.event_type)}
                      {item.read_status === 'UNREAD' && (
                        <span className={styles.unreadDot} title="Unread" />
                      )}
                    </div>
                    <span className={styles.itemTime}>{formatRelativeTime(item.created_at)}</span>
                  </div>

                  <div className={styles.itemSubject}>{item.subject}</div>
                  <p className={styles.itemPreview}>{item.preview}</p>

                  {item.read_status === 'UNREAD' && (
                    <div className={styles.itemActions}>
                      <button
                        type="button"
                        className={styles.markReadBtn}
                        onClick={(e) => handleMarkAsRead(e, item.id)}
                        disabled={markReadMutation.isPending}
                        data-testid={`mark-read-${item.id}`}
                      >
                        <Check size={12} />
                        Mark as read
                      </button>
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className={styles.emptyState} data-testid="notifications-empty-state">
                <Inbox size={28} className={styles.emptyIcon} />
                <p className={styles.emptyTitle}>
                  {unreadOnly ? 'No unread notifications' : 'No notifications yet'}
                </p>
                <p className={styles.emptySubtitle}>
                  {unreadOnly
                    ? "You've caught up with all your unread alerts."
                    : 'Important degree planning and advisor updates will appear here.'}
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
