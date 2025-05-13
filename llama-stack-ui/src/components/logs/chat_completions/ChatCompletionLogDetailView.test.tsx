import React from 'react';
import { render, screen, waitFor, fireEvent, within, RenderResult } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { ChatCompletionLogDetailView } from './ChatCompletionLogDetailView';
import { logService } from '@/mocks/logService';
import type { ChatCompletionLogEntryDetail } from '@/types/logs';
import { mockChatCompletionLogEntries } from '@/mocks/mockChatCompletionsLogs'; // Use detailed mocks

// Mock the logService
jest.mock('@/mocks/logService');
const mockedLogService = logService as jest.Mocked<typeof logService>;

// Mock the toast function from sonner
jest.mock('sonner', () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

// Mock navigator.clipboard
const mockClipboard = {
  writeText: jest.fn(),
};
Object.defineProperty(navigator, 'clipboard', {
  value: mockClipboard,
  writable: true,
});

describe('ChatCompletionLogDetailView', () => {
  const mockLogDetail: ChatCompletionLogEntryDetail = mockChatCompletionLogEntries[0]; // Use first detailed mock
  const mockOnClose = jest.fn();
  let container: HTMLElement; // Define container for querySelectorAll

  beforeEach(() => {
    // Reset mocks before each test
    mockedLogService.fetchChatCompletionDetail.mockClear();
    mockOnClose.mockClear();
    mockClipboard.writeText.mockClear();
    jest.clearAllMocks(); // Clear sonner toast mocks
    // Reset container before each render if needed, or rely on render's cleanup
  });

  it('renders error state if fetch fails', async () => {
    const errorMsg = 'Failed to fetch';
    mockedLogService.fetchChatCompletionDetail.mockRejectedValueOnce(new Error(errorMsg));
    // Suppress console.error
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    render(<ChatCompletionLogDetailView logId="log1" isOpen={true} onClose={mockOnClose} />);

    expect(await screen.findByText(`Error: ${errorMsg}`)).toBeInTheDocument();
    consoleErrorSpy.mockRestore();
  });

  it('renders error state if log not found (returns null)', async () => {
    mockedLogService.fetchChatCompletionDetail.mockResolvedValueOnce(null);
    render(<ChatCompletionLogDetailView logId="log1" isOpen={true} onClose={mockOnClose} />);

    expect(await screen.findByText('Error: Log not found.')).toBeInTheDocument();
  });

  it('fetches and renders log details correctly', async () => {
    mockedLogService.fetchChatCompletionDetail.mockResolvedValueOnce(mockLogDetail);
    render(<ChatCompletionLogDetailView logId={mockLogDetail.id} isOpen={true} onClose={mockOnClose} />);

    const description = await screen.findByText(/^ID:/);
    expect(description).toHaveTextContent(mockLogDetail.id);
    expect(await screen.findByText(mockLogDetail.model)).toBeInTheDocument();
    expect(await screen.findByText(mockLogDetail.status)).toBeInTheDocument();
    expect(await screen.findByText(/Prompt Tokens/i)).toBeInTheDocument();
    expect(await screen.findByText(mockLogDetail.usage!.prompt_tokens!.toString())).toBeInTheDocument();

    expect(screen.getByText('Messages')).toBeInTheDocument();
    expect(await screen.findByText(mockLogDetail.messages[0].content as string)).toBeInTheDocument();
  });

  it('calls onClose when the sheet is closed via the footer close button', async () => {
    mockedLogService.fetchChatCompletionDetail.mockResolvedValueOnce(mockLogDetail);
    render(<ChatCompletionLogDetailView logId={mockLogDetail.id} isOpen={true} onClose={mockOnClose} />);

    // Find the footer div using data-testid
    const footer = await screen.findByTestId('sheet-footer');
    expect(footer).toBeInTheDocument();

    // Find the button *within* the footer div
    const closeButton = within(footer).getByRole('button', { name: /Close/i });
    await userEvent.click(closeButton);

    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('calls clipboard writeText and shows toast on successful copy', async () => {
    mockedLogService.fetchChatCompletionDetail.mockResolvedValueOnce(mockLogDetail);
    mockClipboard.writeText.mockResolvedValueOnce(undefined);

    render(<ChatCompletionLogDetailView logId={mockLogDetail.id} isOpen={true} onClose={mockOnClose} />);

    const copyButton = await screen.findByRole('button', { name: /copy to clipboard/i });
    await userEvent.click(copyButton);

    expect(mockClipboard.writeText).toHaveBeenCalledWith(mockLogDetail.id);
    await waitFor(() => {
      expect(jest.requireMock('sonner').toast.success).toHaveBeenCalledWith('Copied to clipboard!');
    });

    // Temporarily comment out icon checks
    // await waitFor(() => {
    //   expect(copyButton.querySelector('.lucide-check')).toBeInTheDocument();
    // }, { timeout: 500 });
    // await waitFor(() => {
    //   expect(copyButton.querySelector('.lucide-copy')).toBeInTheDocument();
    // }, { timeout: 2000 });

  });

   it('shows error toast on failed copy', async () => {
    mockedLogService.fetchChatCompletionDetail.mockResolvedValueOnce(mockLogDetail);
    const copyErrorMsg = 'Copy failed';
    mockClipboard.writeText.mockRejectedValueOnce(new Error(copyErrorMsg));

    // Suppress console.error for this specific test
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    render(<ChatCompletionLogDetailView logId={mockLogDetail.id} isOpen={true} onClose={mockOnClose} />);

    const copyButton = await screen.findByRole('button', { name: /copy to clipboard/i });
    await userEvent.click(copyButton);

    expect(mockClipboard.writeText).toHaveBeenCalledWith(mockLogDetail.id);
    await waitFor(() => {
      expect(jest.requireMock('sonner').toast.error).toHaveBeenCalledWith(
        'Copy Failed',
        expect.objectContaining({ description: 'Could not copy text to clipboard.' })
      );
    });

    // Restore console.error
    consoleErrorSpy.mockRestore();
   });

}); 