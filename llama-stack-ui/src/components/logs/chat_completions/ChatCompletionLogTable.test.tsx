import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ChatCompletionLogTable } from './ChatCompletionLogTable';
import type { ChatCompletionLogEntrySummary } from '@/types/logs';

// Mock data for testing
const mockLogs: ChatCompletionLogEntrySummary[] = [
  {
    id: 'log1',
    timestamp: new Date().toISOString(),
    model: 'gpt-test',
    status: 'Success',
    inputPreview: 'Input 1 preview...',
    outputPreview: 'Output 1 preview...',
    durationFormatted: '1.23s',
  },
  {
    id: 'log2',
    timestamp: new Date(Date.now() - 60000).toISOString(), // 1 min ago
    model: 'llama-test',
    status: 'Error',
    inputPreview: 'Input 2 preview...',
    outputPreview: 'Error preview...',
    durationFormatted: '0.50s',
  },
];

describe('ChatCompletionLogTable', () => {
  it('renders table headers correctly', () => {
    render(<ChatCompletionLogTable chatCompletionLogs={[]} isLoading={false} error={null} />);
    expect(screen.getByRole('columnheader', { name: /timestamp/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /status/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /model/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /input/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /output/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /duration/i })).toBeInTheDocument();
  });

  it('renders log data correctly', () => {
    render(<ChatCompletionLogTable chatCompletionLogs={mockLogs} isLoading={false} error={null} />);

    // Check first row data
    expect(screen.getByText('gpt-test')).toBeInTheDocument();
    expect(screen.getByText('Success')).toBeInTheDocument();
    expect(screen.getByText(/Input 1 preview.../i)).toBeInTheDocument();
    expect(screen.getByText(/Output 1 preview.../i)).toBeInTheDocument();
    expect(screen.getByText('1.23s')).toBeInTheDocument();

    // Check second row data
    expect(screen.getByText('llama-test')).toBeInTheDocument();
    expect(screen.getByText('Error')).toBeInTheDocument(); // Badge text
    expect(screen.getByText(/Input 2 preview.../i)).toBeInTheDocument();
    expect(screen.getByText(/Error preview.../i)).toBeInTheDocument();
    expect(screen.getByText('0.50s')).toBeInTheDocument();
  });

  it('renders loading state with skeletons', () => {
    render(<ChatCompletionLogTable chatCompletionLogs={[]} isLoading={true} error={null} />);
    // Check that headers ARE present
    expect(screen.getByRole('columnheader', { name: /timestamp/i })).toBeInTheDocument();

    // Check that skeleton elements are rendered within table cells
    // We expect 3 skeleton rows * 6 columns = 18 skeleton divs
    const skeletons = screen.getAllByTestId('skeleton'); // Assuming Skeleton component has data-testid="skeleton"
    expect(skeletons.length).toBe(18); 

    // Check that actual data text is NOT present
    expect(screen.queryByText('gpt-test')).not.toBeInTheDocument();
    expect(screen.queryByText('Success')).not.toBeInTheDocument();

  });

  it('renders error state', () => {
    const testError = new Error('Failed to load data');
    render(<ChatCompletionLogTable chatCompletionLogs={[]} isLoading={false} error={testError} />);
    expect(screen.getByText(/Error loading logs: Failed to load data/i)).toBeInTheDocument();
  });

  it('renders empty state inside table body', () => {
    render(<ChatCompletionLogTable chatCompletionLogs={[]} isLoading={false} error={null} />);
    // Headers should still be present
    expect(screen.getByRole('columnheader', { name: /timestamp/i })).toBeInTheDocument();
    // Check for the empty message within a table cell
    const cell = screen.getByRole('cell');
    expect(cell).toHaveTextContent(/No logs found./i);
    expect(cell).toHaveAttribute('colSpan', '6'); // Check it spans 6 columns
  });
}); 