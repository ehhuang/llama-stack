import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import Home from './chat_completions/page'; // Import the page component
import { logService } from '@/mocks/logService'; // Import the service to mock
import type { MockChatCompletionLogListResponse } from '@/types/logs';

// Mock the logService
// We need to mock the whole module since fetchChatCompletionList is exported within an object
jest.mock('@/mocks/logService');

// Define the type for the mocked service
const mockedLogService = logService as jest.Mocked<typeof logService>;

// Mock data to be returned by the service
const mockApiResponse: MockChatCompletionLogListResponse = {
  logs: [
    {
      id: 'log-int1',
      timestamp: new Date().toISOString(),
      model: 'gpt-int-test',
      status: 'Success',
      inputPreview: 'Integration input...',
      outputPreview: 'Integration output...',
      durationFormatted: '0.99s',
    },
  ],
  totalCount: 1,
};

describe('Home Page Integration', () => {
  beforeEach(() => {
    // Reset mocks before each test
    mockedLogService.fetchChatCompletionList.mockClear();
  });

  it('fetches logs on mount and renders the table', async () => {
    // Setup the mock implementation for this test
    mockedLogService.fetchChatCompletionList.mockResolvedValueOnce(mockApiResponse);

    render(<Home />);

    // Check that the loading state is initially shown (via skeleton check in unit test)
    // Here, we wait for the data to load and the table to appear

    // Check if the service function was called
    expect(mockedLogService.fetchChatCompletionList).toHaveBeenCalledTimes(1);

    // Wait for the table headers to be rendered after loading
    await waitFor(() => {
      expect(screen.getByRole('columnheader', { name: /timestamp/i })).toBeInTheDocument();
    });

    // Check if the data from the mock response is rendered using findBy* which waits
    expect(await screen.findByText('gpt-int-test')).toBeInTheDocument();
    expect(await screen.findByText(/Integration input.../i)).toBeInTheDocument();
    expect(await screen.findByText(/Integration output.../i)).toBeInTheDocument();
    expect(await screen.findByText('0.99s')).toBeInTheDocument();
  });

  it('displays an error message if fetching logs fails', async () => {
    const errorMessage = 'Network Error';
    // Setup the mock to reject
    mockedLogService.fetchChatCompletionList.mockRejectedValueOnce(
      new Error(errorMessage),
    );

    // Suppress console.error for this specific test
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    render(<Home />);

    // Wait for the error message to appear
    await waitFor(() => {
      expect(
        screen.getByText(`Error loading logs: ${errorMessage}`),
      ).toBeInTheDocument();
    });

    // Ensure table data isn't rendered
    expect(screen.queryByText('gpt-int-test')).not.toBeInTheDocument();

    // Restore console.error
    consoleErrorSpy.mockRestore();
  });
}); 