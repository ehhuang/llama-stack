import { ChatCompletionLogEntryDetail, LogMessage } from "@/types/logs";
import LlamaStackClient from "llama-stack-client";

// Singleton client instance
const llamaClient = new LlamaStackClient({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8321",
});

// Helper: Map OpenAIMessageParam (backend) to LogMessage (frontend)
function mapOpenAIMessageToLogMessage(msg: any): LogMessage {
  return {
    role: msg.role,
    content: msg.content ?? null,
    name: msg.name,
    tool_calls: msg.tool_calls,
    tool_call_id: msg.tool_call_id,
  };
}

// Main API fetch function
export async function fetchChatCompletionDetailFromAPI(
  logId: string
): Promise<ChatCompletionLogEntryDetail | null> {
  try {
    // Use the SDK method
    const data = await llamaClient.log.getChatCompletion(logId);
    // Map backend ChatCompletion to frontend ChatCompletionLogEntryDetail
    const detail: ChatCompletionLogEntryDetail = {
      id: data.id,
      timestamp: new Date(data.created * 1000).toISOString(),
      model: data.model,
      status: "Success",
      messages: Array.isArray(data.messages)
        ? data.messages.map(mapOpenAIMessageToLogMessage)
        : [],
      // The following fields are not present in backend, so set as undefined
      durationMs: undefined,
      usage: undefined,
      cost: undefined,
      tags: undefined,
      error: undefined,
    };
    return detail;
  } catch (err: any) {
    // Optionally log error
    return null;
  }
}

// Helper: Generate preview string from message content
function getMessageContentAsString(content: any): string {
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) return content.map(getMessageContentAsString).join(' ');
  if (content && typeof content === 'object' && content.text) return content.text;
  return '';
}

function generatePreview(str: string, maxLen = 60): string {
  if (!str) return '';
  return str.length > maxLen ? str.slice(0, maxLen) + '…' : str;
}

function createSummaryFromDetail(entry: any): import("@/types/logs").ChatCompletionLogEntrySummary {
  let inputPreview = '';
  let outputPreview = '';

  // Gather all messages except the last assistant message as inputs
  const messages = Array.isArray(entry.messages) ? entry.messages : [];
  // Find the last assistant message index
  const lastAssistantIdx = [...messages].reverse().findIndex((m: any) => m.role === 'assistant');
  const lastAssistantAbsIdx = lastAssistantIdx !== -1 ? messages.length - 1 - lastAssistantIdx : -1;

  // Inputs: all messages except the last assistant message
  const inputMessages = messages.filter((_: any, idx: number) => idx !== lastAssistantAbsIdx);
  inputPreview = inputMessages
    .map((m: any) => {
      if (["user", "system", "tool"].includes(m.role)) {
        return getMessageContentAsString(m.content);
      }
      return '';
    })
    .filter(Boolean)
    .join(' | ');

  // Output: last assistant message (or error)
  let status: 'Success' | 'Error' = 'Success';
  if (entry.status === 'Error') status = 'Error';
  if (status === 'Error' && entry.error) {
    outputPreview = generatePreview(`Error: ${entry.error.message ?? 'Unknown error'}`);
  } else if (lastAssistantAbsIdx !== -1) {
    const lastAssistantMessage = messages[lastAssistantAbsIdx];
    outputPreview = generatePreview(getMessageContentAsString(lastAssistantMessage.content));
    if (!lastAssistantMessage.content && lastAssistantMessage.tool_calls) {
      outputPreview = `[Tool Call: ${lastAssistantMessage.tool_calls[0]?.function?.name ?? '...'}]`;
    }
  }

  return {
    id: entry.id,
    timestamp: new Date(entry.created * 1000).toISOString(),
    model: entry.model,
    status,
    inputPreview,
    outputPreview,
    durationFormatted: undefined, // Not available from API
  };
}

export async function fetchChatCompletionListFromAPI(): Promise<{ logs: import("@/types/logs").ChatCompletionLogEntrySummary[]; totalCount: number }> {
  try {
    // Use the SDK method (returns an array)
    const completions = await llamaClient.log.listChatCompletions();
    const logs = Array.isArray(completions)
      ? completions.map(createSummaryFromDetail)
      : [];
    return { logs, totalCount: logs.length };
  } catch (err: any) {
    // Optionally log error
    return { logs: [], totalCount: 0 };
  }
} 