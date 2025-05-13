import {
  ChatCompletionLogEntryDetail,
  ChatCompletionLogEntrySummary,
  LogMessage,
  MockChatCompletionLogListResponse,
} from '@/types/logs';
import { mockChatCompletionLogEntries } from './mockChatCompletionsLogs';

// --- Helper Functions ---

// Simple function to simulate network delay
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// Helper to safely get string content for preview
const getMessageContentAsString = (content: any): string => {
  if (typeof content === 'string') {
    return content;
  }
  if (Array.isArray(content) && content.length > 0 && content[0]?.text) {
    // Handle OpenAI structure like [{ type: 'text', text: '...' }]
    return content[0].text;
  }
  // Add more complex handling if needed for other structures
  return '';
};

// Generate preview text (simple truncation)
const generatePreview = (text: string | null | undefined, length = 100): string => {
  if (!text) return '';
  return text.length > length ? text.substring(0, length) + '...' : text;
};

// Format duration (ms to s)
const formatDuration = (ms: number | undefined): string | undefined => {
  if (ms === undefined) return undefined;
  return (ms / 1000).toFixed(2) + 's';
};

// Generate summary object from detail
const createSummary = (
  entry: ChatCompletionLogEntryDetail,
): ChatCompletionLogEntrySummary => {
  let inputPreview = '';
  let outputPreview = '';

  // Gather all messages except the last assistant message as inputs
  const messages = entry.messages;
  // Find the last assistant message index
  const lastAssistantIdx = [...messages].reverse().findIndex((m) => m.role === 'assistant');
  const lastAssistantAbsIdx = lastAssistantIdx !== -1 ? messages.length - 1 - lastAssistantIdx : -1;

  // Inputs: all messages except the last assistant message
  const inputMessages = messages.filter((_, idx) => idx !== lastAssistantAbsIdx);
  inputPreview = inputMessages
    .map((m) => {
      // Only show user, system, and tool messages as input context
      if (['user', 'system', 'tool'].includes(m.role)) {
        return getMessageContentAsString(m.content);
      }
      return '';
    })
    .filter(Boolean)
    .join(' | ');

  // Output: last assistant message (or error)
  if (entry.status === 'Error') {
    outputPreview = generatePreview(`Error: ${entry.error?.message ?? 'Unknown error'}`);
  } else if (lastAssistantAbsIdx !== -1) {
    const lastAssistantMessage = messages[lastAssistantAbsIdx];
    outputPreview = generatePreview(getMessageContentAsString(lastAssistantMessage.content));
    if (!lastAssistantMessage.content && lastAssistantMessage.tool_calls) {
      outputPreview = `[Tool Call: ${lastAssistantMessage.tool_calls[0]?.function?.name ?? '...'}]`;
    }
  }

  return {
    id: entry.id,
    timestamp: entry.timestamp,
    model: entry.model,
    status: entry.status,
    inputPreview,
    outputPreview,
    durationFormatted: formatDuration(entry.durationMs),
  };
};

// --- Mock Service Options --- (Define interface for clarity)

interface FetchChatCompletionListOptions {
  page?: number; // 1-based page number
  limit?: number; // Items per page
  sortBy?: keyof ChatCompletionLogEntrySummary | keyof ChatCompletionLogEntryDetail;
  sortDirection?: 'asc' | 'desc';
  filters?: {
    dateRange?: { start?: string; end?: string }; // ISO strings
    model?: string[];
    status?: ('Success' | 'Error')[];
    query?: string; // Free-text search term
    // TODO: Add filters for tags, tool calls if needed later
  };
}

// --- Mock Service Implementation ---

async function fetchChatCompletionList(
  options: FetchChatCompletionListOptions = {},
): Promise<MockChatCompletionLogListResponse> {
  await sleep(300); // Simulate network delay

  const { page = 1, limit = 10, sortBy = 'timestamp', sortDirection = 'desc', filters = {} } = options;

  let filteredEntries = [...mockChatCompletionLogEntries];

  // Apply Filtering
  if (filters.status && filters.status.length > 0) {
    filteredEntries = filteredEntries.filter((entry) =>
      filters.status?.includes(entry.status),
    );
  }
  if (filters.model && filters.model.length > 0) {
    filteredEntries = filteredEntries.filter((entry) =>
      filters.model?.includes(entry.model),
    );
  }
  if (filters.dateRange?.start) {
    filteredEntries = filteredEntries.filter(
      (entry) => entry.timestamp >= filters.dateRange!.start!,
    );
  }
  if (filters.dateRange?.end) {
    filteredEntries = filteredEntries.filter(
      (entry) => entry.timestamp <= filters.dateRange!.end!,
    );
  }
  if (filters.query) {
    const queryLower = filters.query.toLowerCase();
    filteredEntries = filteredEntries.filter((entry) => {
      // Search in ID, model, previews, error messages
      const userContent = getMessageContentAsString(
        entry.messages.find((m) => m.role === 'user')?.content,
      );
      const assistantContent = getMessageContentAsString(
        entry.messages.find((m) => m.role === 'assistant')?.content,
      );
      return (
        entry.id.toLowerCase().includes(queryLower) ||
        entry.model.toLowerCase().includes(queryLower) ||
        userContent.toLowerCase().includes(queryLower) ||
        assistantContent.toLowerCase().includes(queryLower) ||
        (entry.status === 'Error' &&
          entry.error?.message.toLowerCase().includes(queryLower))
      );
    });
  }

  // Apply Sorting (only timestamp implemented for now)
  // TODO: Implement sorting for other columns if needed
  if (sortBy === 'timestamp') {
    filteredEntries.sort((a, b) => {
      const dateA = new Date(a.timestamp).getTime();
      const dateB = new Date(b.timestamp).getTime();
      return sortDirection === 'desc' ? dateB - dateA : dateA - dateB;
    });
  }

  // Apply Pagination
  const totalCount = filteredEntries.length;
  const startIndex = (page - 1) * limit;
  const endIndex = startIndex + limit;
  const paginatedEntries = filteredEntries.slice(startIndex, endIndex);

  // Create Summary objects
  const summaries = paginatedEntries.map(createSummary);

  return {
    logs: summaries,
    totalCount,
  };
}

async function fetchChatCompletionDetail(
  id: string,
): Promise<ChatCompletionLogEntryDetail | null> {
  await sleep(150); // Simulate network delay

  const entry = mockChatCompletionLogEntries.find((log) => log.id === id);

  if (!entry) {
    // Simulate not found error
    // In a real API, this might throw an error or return a specific status
    console.warn(`Mock log with id ${id} not found.`);
    return null;
  }

  return entry;
}

export const logService = {
  fetchChatCompletionList,
  fetchChatCompletionDetail,
}; 