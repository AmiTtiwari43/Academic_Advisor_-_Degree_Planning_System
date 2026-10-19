import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AssistantDrawer } from '../AssistantDrawer';
import { assistantApi, AssistantResponse, AssistantCapabilities } from '../../../api/assistant';

const mockCapabilities: AssistantCapabilities = {
  supported_query_types: [
    'Course prerequisite validation',
    'Degree progress and graduation credit summary',
    'Remaining mandatory course requirements',
    'Institution course catalog exploration',
  ],
  disclaimer:
    "AI responses are strictly grounded in your institution's published curriculum and official degree audit records.",
  grounding_sources: ['Published Curriculum Versions', 'Degree Audit Engine'],
  rate_limit: '20 requests per minute per user',
};

const mockQueryResponse: AssistantResponse = {
  answer:
    '**CS201 - Data Structures**: All prerequisites are **satisfied** based on your official academic transcript. Course CS101 completed with grade A.',
  citations: [
    {
      source_type: 'RULE_ENGINE',
      reference: 'Prerequisite Interpreter [CS201]',
      details: 'Rule result: SATISFIED. Requires CS101.',
    },
    {
      source_type: 'CURRICULUM_CATALOG',
      reference: 'Curriculum CS-BS v1, Course CS201',
      details: 'Data Structures (4.0 credits)',
    },
  ],
  grounded_context_summary: 'Grounded in 3 catalog courses and official degree audit records.',
  disclaimer:
    "AI responses are strictly grounded in your institution's published curriculum and official degree audit records.",
};

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('AssistantDrawer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(assistantApi, 'getCapabilities').mockResolvedValue(mockCapabilities);
  });

  it('does not render when isOpen is false', () => {
    renderWithClient(<AssistantDrawer isOpen={false} onClose={vi.fn()} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders drawer header, regulatory disclaimer, and rate limit when open', async () => {
    renderWithClient(<AssistantDrawer isOpen={true} onClose={vi.fn()} />);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Academic AI Advisor')).toBeInTheDocument();
    expect(screen.getByText('20 req/min')).toBeInTheDocument();
    expect(
      screen.getByText(/AI responses are strictly grounded in your institution's published curriculum/i)
    ).toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', () => {
    const handleClose = vi.fn();
    renderWithClient(<AssistantDrawer isOpen={true} onClose={handleClose} />);

    const closeBtn = screen.getByRole('button', { name: /close assistant drawer/i });
    fireEvent.click(closeBtn);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('calls onClose when Escape key is pressed', () => {
    const handleClose = vi.fn();
    renderWithClient(<AssistantDrawer isOpen={true} onClose={handleClose} />);

    fireEvent.keyDown(window, { key: 'Escape' });
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('renders suggested inquiries in the empty welcome state', () => {
    renderWithClient(<AssistantDrawer isOpen={true} onClose={vi.fn()} />);

    expect(screen.getByText('Can I take CS201 next semester?')).toBeInTheDocument();
    expect(screen.getByText('How many remaining credits do I need to graduate?')).toBeInTheDocument();
  });

  it('submits a user question and displays grounded response with citations', async () => {
    vi.spyOn(assistantApi, 'query').mockResolvedValue(mockQueryResponse);

    renderWithClient(<AssistantDrawer isOpen={true} onClose={vi.fn()} />);

    const input = screen.getByPlaceholderText(/Ask about prerequisites, degree progress, courses/i);
    fireEvent.change(input, { target: { value: 'Can I take CS201 next semester?' } });

    const sendBtn = screen.getByLabelText('Send query');
    fireEvent.click(sendBtn);

    // Verify user question displayed
    expect(screen.getByText('Can I take CS201 next semester?')).toBeInTheDocument();

    // Await assistant answer
    await waitFor(() => {
      expect(screen.getByText(/All prerequisites are/i)).toBeInTheDocument();
    });

    // Verify citations
    expect(screen.getByText('RULE_ENGINE')).toBeInTheDocument();
    expect(screen.getByText('Prerequisite Interpreter [CS201]')).toBeInTheDocument();
    expect(screen.getByText('CURRICULUM_CATALOG')).toBeInTheDocument();
    expect(screen.getByText(/Grounded in 3 catalog courses/i)).toBeInTheDocument();
  });

  it('clicking a suggestion chip triggers the query immediately', async () => {
    const querySpy = vi.spyOn(assistantApi, 'query').mockResolvedValue(mockQueryResponse);

    renderWithClient(<AssistantDrawer isOpen={true} onClose={vi.fn()} />);

    const chip = screen.getByText('Can I take CS201 next semester?');
    fireEvent.click(chip);

    await waitFor(() => {
      expect(querySpy).toHaveBeenCalledWith({
        prompt: 'Can I take CS201 next semester?',
        student_record_id: undefined,
      });
    });
  });

  it('handles query errors gracefully', async () => {
    vi.spyOn(assistantApi, 'query').mockRejectedValue({
      response: { data: { detail: 'Active institutional context required.' } },
    });

    renderWithClient(<AssistantDrawer isOpen={true} onClose={vi.fn()} />);

    const input = screen.getByPlaceholderText(/Ask about prerequisites, degree progress, courses/i);
    fireEvent.change(input, { target: { value: 'Can I take CS201?' } });

    const sendBtn = screen.getByLabelText('Send query');
    fireEvent.click(sendBtn);

    await waitFor(() => {
      expect(
        screen.getByText('Active institutional context required.')
      ).toBeInTheDocument();
    });
  });
});
