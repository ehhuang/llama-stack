// src/types/logs.ts

// Representing message content (simplified for mock)
// Using 'any' temporarily for flexibility in mock data; can be refined later.
type MessageContent = string | { type: string; [key: string]: any }[] | any; 

// Representing a message in the conversation log
export interface LogMessage {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: MessageContent | null;
  name?: string;
  // Tool calls requested by the assistant
  tool_calls?: { id: string; type: 'function'; function: { name: string; arguments: string } }[];
  // ID for the tool call this message is a response to (for role: 'tool')
  tool_call_id?: string;
}

// Representing the detailed structure of a single chat completion log entry
export interface ChatCompletionLogEntryDetail {
  id: string; // Unique Call ID / Trace ID (e.g., from OpenAI response header or trace system)
  timestamp: string; // ISO 8601 format string for when the log was recorded/completed
  model: string; // Model ID used (e.g., "gpt-4o-mini")
  status: 'Success' | 'Error'; // Status of the API call
  error?: {
    message: string;
    code?: string | number; // e.g., HTTP status code or specific error code
    type?: string; // e.g., "invalid_request_error"
  };
  durationMs?: number; // Duration of the API call in milliseconds
  usage?: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
  };
  cost?: number; // Calculated cost in USD (optional)
  tags?: Record<string, string>; // User-defined or system-defined metadata/tags
  messages: LogMessage[]; // The sequence of messages in the chat interaction
  // Potentially add backend-specific wrapper fields if needed, like API request ID, user ID, etc.
}

// Representing the summarized structure for the table view
export interface ChatCompletionLogEntrySummary
  extends Pick<
    ChatCompletionLogEntryDetail,
    'id' | 'timestamp' | 'model' | 'status'
  > {
  inputPreview: string; // First part of the primary user input message content
  outputPreview: string; // First part of the assistant output message content or error message
  durationFormatted?: string; // Optional formatted duration (e.g., "1.23s") for display
  // We might add token counts or cost here later if needed for the table
}

// Type for the response of the mock list endpoint
export interface MockChatCompletionLogListResponse {
  logs: ChatCompletionLogEntrySummary[];
  totalCount: number; // Total number of logs matching filters (for pagination calculations)
  // Optionally add other pagination metadata like hasMore, cursor, etc.
} 