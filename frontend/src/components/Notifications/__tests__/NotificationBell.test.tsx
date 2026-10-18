import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { NotificationBell } from '../NotificationBell';
import { notificationsApi, NotificationItem } from '../../../api/notifications';

const mockNotifications: NotificationItem[] = [
  {
    id: 'n-1',
    institution: 'inst-1',
    recipient: 1,
    event_type: 'PLAN_SUBMITTED',
    subject: 'Plan Submission: CS Major Plan',
    preview: 'A degree plan CS Major Plan has been submitted for advisor review.',
    payload: { plan_id: 'p-1' },
    delivery_status: 'DELIVERED',
    read_status: 'UNREAD',
    read_at: null,
    created_at: new Date(Date.now() - 5 * 60000).toISOString(), // 5m ago
  },
  {
    id: 'n-2',
    institution: 'inst-1',
    recipient: 1,
    event_type: 'PLAN_APPROVED',
    subject: 'Plan Update: CS Major Plan',
    preview: 'Your degree plan CS Major Plan has received an academic review update.',
    payload: { plan_id: 'p-1', action: 'APPROVE' },
    delivery_status: 'DELIVERED',
    read_status: 'READ',
    read_at: new Date(Date.now() - 60 * 60000).toISOString(),
    created_at: new Date(Date.now() - 120 * 60000).toISOString(), // 2h ago
  },
];

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('NotificationBell', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders bell button and does not show badge count when unread count is 0', async () => {
    vi.spyOn(notificationsApi, 'getUnreadCount').mockResolvedValue({ unread_count: 0 });

    renderWithClient(<NotificationBell />);

    const bellBtn = screen.getByTestId('notification-bell-btn');
    expect(bellBtn).toBeInTheDocument();
    expect(screen.queryByTestId('notification-badge-count')).not.toBeInTheDocument();
  });

  it('displays badge count badge when unread notifications exist', async () => {
    vi.spyOn(notificationsApi, 'getUnreadCount').mockResolvedValue({ unread_count: 5 });

    renderWithClient(<NotificationBell />);

    const badge = await screen.findByTestId('notification-badge-count');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('5');
  });

  it('caps badge count to 99+ when unread count exceeds 99', async () => {
    vi.spyOn(notificationsApi, 'getUnreadCount').mockResolvedValue({ unread_count: 120 });

    renderWithClient(<NotificationBell />);

    const badge = await screen.findByTestId('notification-badge-count');
    expect(badge).toHaveTextContent('99+');
  });

  it('toggles notifications dropdown on bell click and loads notifications list', async () => {
    vi.spyOn(notificationsApi, 'getUnreadCount').mockResolvedValue({ unread_count: 1 });
    vi.spyOn(notificationsApi, 'listNotifications').mockResolvedValue(mockNotifications);

    renderWithClient(<NotificationBell />);

    const bellBtn = screen.getByTestId('notification-bell-btn');
    fireEvent.click(bellBtn);

    expect(screen.getByRole('dialog', { name: /notifications panel/i })).toBeInTheDocument();
    expect(screen.getByText('Notifications')).toBeInTheDocument();

    expect(await screen.findByText('Plan Submission: CS Major Plan')).toBeInTheDocument();
    expect(screen.getByText('Plan Update: CS Major Plan')).toBeInTheDocument();
    expect(screen.getByText('Submitted')).toBeInTheDocument();
    expect(screen.getByText('Approved')).toBeInTheDocument();
  });

  it('calls markAsRead when individual mark as read button is clicked', async () => {
    vi.spyOn(notificationsApi, 'getUnreadCount').mockResolvedValue({ unread_count: 1 });
    vi.spyOn(notificationsApi, 'listNotifications').mockResolvedValue(mockNotifications);
    const markReadSpy = vi.spyOn(notificationsApi, 'markAsRead').mockResolvedValue({
      ...mockNotifications[0],
      read_status: 'READ',
      read_at: new Date().toISOString(),
    });

    renderWithClient(<NotificationBell />);

    await screen.findByTestId('notification-badge-count');
    fireEvent.click(screen.getByTestId('notification-bell-btn'));

    const markBtn = await screen.findByTestId('mark-read-n-1');
    expect(markBtn).toBeInTheDocument();

    fireEvent.click(markBtn);
    await waitFor(() => {
      expect(markReadSpy).toHaveBeenCalledWith('n-1');
    });
  });

  it('calls markAllAsRead when Mark all read button is clicked', async () => {
    vi.spyOn(notificationsApi, 'getUnreadCount').mockResolvedValue({ unread_count: 2 });
    vi.spyOn(notificationsApi, 'listNotifications').mockResolvedValue(mockNotifications);
    const markAllSpy = vi.spyOn(notificationsApi, 'markAllAsRead').mockResolvedValue({
      updated_count: 2,
    });

    renderWithClient(<NotificationBell />);

    await screen.findByTestId('notification-badge-count');
    fireEvent.click(screen.getByTestId('notification-bell-btn'));

    const markAllBtn = await screen.findByTestId('mark-all-read-btn');
    expect(markAllBtn).not.toBeDisabled();

    fireEvent.click(markAllBtn);
    await waitFor(() => {
      expect(markAllSpy).toHaveBeenCalledTimes(1);
    });
  });

  it('supports filtering by Unread only', async () => {
    vi.spyOn(notificationsApi, 'getUnreadCount').mockResolvedValue({ unread_count: 1 });
    const listSpy = vi.spyOn(notificationsApi, 'listNotifications').mockResolvedValue([mockNotifications[0]]);

    renderWithClient(<NotificationBell />);

    fireEvent.click(screen.getByTestId('notification-bell-btn'));

    const unreadTab = await screen.findByTestId('filter-unread-btn');
    fireEvent.click(unreadTab);

    await waitFor(() => {
      expect(listSpy).toHaveBeenCalledWith(true);
    });
  });

  it('displays empty state when no notifications are returned', async () => {
    vi.spyOn(notificationsApi, 'getUnreadCount').mockResolvedValue({ unread_count: 0 });
    vi.spyOn(notificationsApi, 'listNotifications').mockResolvedValue([]);

    renderWithClient(<NotificationBell />);

    fireEvent.click(screen.getByTestId('notification-bell-btn'));

    expect(await screen.findByTestId('notifications-empty-state')).toBeInTheDocument();
    expect(screen.getByText('No notifications yet')).toBeInTheDocument();
  });

  it('closes dropdown when Escape key is pressed', async () => {
    vi.spyOn(notificationsApi, 'getUnreadCount').mockResolvedValue({ unread_count: 0 });
    vi.spyOn(notificationsApi, 'listNotifications').mockResolvedValue([]);

    renderWithClient(<NotificationBell />);

    fireEvent.click(screen.getByTestId('notification-bell-btn'));
    expect(screen.getByRole('dialog', { name: /notifications panel/i })).toBeInTheDocument();

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('dialog', { name: /notifications panel/i })).not.toBeInTheDocument();
  });
});
