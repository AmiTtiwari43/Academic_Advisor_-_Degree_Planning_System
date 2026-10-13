import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Button } from '../Button/Button';
import { Badge } from '../Badge/Badge';
import { Table, Column } from '../Table/Table';
import { Input } from '../Input/Input';
import { Breadcrumbs } from '../Breadcrumbs/Breadcrumbs';

describe('Design System Components', () => {
  it('renders Button with label and fires onClick event', () => {
    const handleClick = vi.fn();
    render(
      <Button variant="primary" onClick={handleClick}>
        Confirm Degree Plan
      </Button>
    );

    const button = screen.getByRole('button', { name: /confirm degree plan/i });
    expect(button).toBeInTheDocument();
    fireEvent.click(button);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('renders Badge with accessible status label', () => {
    render(<Badge variant="success">Completed</Badge>);
    expect(screen.getByText('Completed')).toBeInTheDocument();
  });

  it('renders Table columns and data rows', () => {
    interface TestItem {
      id: string;
      code: string;
      credits: number;
    }

    const columns: Column<TestItem>[] = [
      { key: 'code', header: 'Course Code' },
      { key: 'credits', header: 'Credits' },
    ];

    const data: TestItem[] = [
      { id: '1', code: 'CS 101', credits: 4 },
      { id: '2', code: 'MATH 151', credits: 4 },
    ];

    render(
      <Table
        columns={columns}
        data={data}
        keyExtractor={(item) => item.id}
        caption="Test Courses"
      />
    );

    expect(screen.getByText('CS 101')).toBeInTheDocument();
    expect(screen.getByText('MATH 151')).toBeInTheDocument();
    expect(screen.getByText('Course Code')).toBeInTheDocument();
  });

  it('renders Table empty state when data array is empty', () => {
    render(
      <Table
        columns={[{ key: 'code', header: 'Course Code' }]}
        data={[]}
        keyExtractor={(item: { code: string }) => item.code}
        emptyState={<div>No curriculum courses registered</div>}
      />
    );

    expect(screen.getByText('No curriculum courses registered')).toBeInTheDocument();
  });

  it('renders Input with accessible label and helper text', () => {
    render(
      <Input
        label="Catalog Year"
        helperText="Enter 4-digit academic year"
        placeholder="e.g. 2025"
      />
    );

    expect(screen.getByLabelText(/catalog year/i)).toBeInTheDocument();
    expect(screen.getByText(/enter 4-digit academic year/i)).toBeInTheDocument();
  });

  it('renders Breadcrumbs navigation trail', () => {
    render(
      <Breadcrumbs
        items={[
          { label: 'Curricula', href: '/curricula' },
          { label: 'Computer Science B.Sc.' },
        ]}
      />
    );

    expect(screen.getByText('Curricula')).toBeInTheDocument();
    expect(screen.getByText('Computer Science B.Sc.')).toBeInTheDocument();
  });
});
