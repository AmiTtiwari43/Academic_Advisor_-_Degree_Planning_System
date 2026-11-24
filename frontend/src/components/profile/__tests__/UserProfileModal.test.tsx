import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { UserProfileModal } from '../UserProfileModal';
import { authApi } from '../../../api/auth';
import { useAuth } from '../../../context/AuthContext';

vi.mock('../../../api/auth', () => ({
  authApi: {
    getProfile: vi.fn(),
    updateProfile: vi.fn(),
  },
}));

vi.mock('../../../context/AuthContext', () => ({
  useAuth: vi.fn(),
}));

const mockUser = {
  id: 'user-123',
  username: 'student_alex',
  first_name: 'Alex',
  last_name: 'Rivera',
  preferred_name: 'Alex R.',
  email: 'alex.rivera@agu.edu',
  phone_number: '+1 (555) 234-5678',
  memberships: [],
  is_staff: false,
  is_superuser: false,
};

const mockProfile = {
  username: 'student_alex',
  first_name: 'Alex',
  last_name: 'Rivera',
  preferred_name: 'Alex R.',
  email: 'alex.rivera@agu.edu',
  phone_number: '+1 (555) 234-5678',
  role: 'STUDENT',
  institution_name: 'Metropolitan State University',
  academic_summary: {
    programme: 'B.S. in Computer Science',
    programme_code: 'BS-CS',
    cgpa: '8.39 / 10.00',
    credits_earned: 58.0,
    status: 'Good Standing',
    enrollment_term: 'Fall 2024',
    advisor: 'Dr. Alice Chen',
  },
};

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('UserProfileModal Component', () => {
  const refreshUserMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useAuth as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      user: mockUser,
      activeRole: 'STUDENT',
      refreshUser: refreshUserMock,
    });
    (authApi.getProfile as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockProfile);
    (authApi.updateProfile as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockProfile);
  });

  it('does not render when isOpen is false', () => {
    renderWithClient(<UserProfileModal isOpen={false} onClose={vi.fn()} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders modal with user details, academic summary on 10-point scale, and editable inputs', async () => {
    renderWithClient(<UserProfileModal isOpen={true} onClose={vi.fn()} />);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Alex R.')).toBeInTheDocument();
    expect(screen.getByText('@student_alex')).toBeInTheDocument();
    expect(screen.getAllByText('STUDENT').length).toBeGreaterThan(0);
    expect(screen.getByText('Metropolitan State University')).toBeInTheDocument();

    // Check academic summary
    await waitFor(() => {
      expect(screen.getByText('8.39 / 10.00')).toBeInTheDocument();
      expect(screen.getByText('58 cr')).toBeInTheDocument();
      expect(screen.getByText('B.S. in Computer Science (BS-CS)')).toBeInTheDocument();
      expect(screen.getByText('Dr. Alice Chen')).toBeInTheDocument();
    });

    // Check input fields
    expect(screen.getByLabelText(/first name/i)).toHaveValue('Alex');
    expect(screen.getByLabelText(/last name/i)).toHaveValue('Rivera');
    expect(screen.getByLabelText(/preferred name/i)).toHaveValue('Alex R.');
    expect(screen.getByLabelText(/institutional email/i)).toHaveValue('alex.rivera@agu.edu');
    expect(screen.getByLabelText(/phone number/i)).toHaveValue('+1 (555) 234-5678');
  });

  it('allows user to edit information and submit updates successfully', async () => {
    renderWithClient(<UserProfileModal isOpen={true} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByLabelText(/first name/i)).toHaveValue('Alex');
    });

    // Change first name & preferred name
    fireEvent.change(screen.getByLabelText(/first name/i), { target: { value: 'Alexander' } });
    fireEvent.change(screen.getByLabelText(/preferred name/i), { target: { value: 'Alex' } });

    // Submit form
    const saveBtn = screen.getByRole('button', { name: /save profile changes/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(authApi.updateProfile).toHaveBeenCalled();
      expect(screen.getByText(/profile information successfully updated/i)).toBeInTheDocument();
      expect(refreshUserMock).toHaveBeenCalled();
    });
  });

  it('calls onClose when close button is clicked', () => {
    const handleClose = vi.fn();
    renderWithClient(<UserProfileModal isOpen={true} onClose={handleClose} />);

    const closeBtn = screen.getByRole('button', { name: /close profile window/i });
    fireEvent.click(closeBtn);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('calls onClose when Escape key is pressed', () => {
    const handleClose = vi.fn();
    renderWithClient(<UserProfileModal isOpen={true} onClose={handleClose} />);

    fireEvent.keyDown(window, { key: 'Escape' });
    expect(handleClose).toHaveBeenCalledTimes(1);
  });
});
