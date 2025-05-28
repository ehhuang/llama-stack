"use client";

import {
  OpenAIResponse,
  ResponseInput,
  ResponseInputMessageContent,
} from "@/lib/types";
import { LogsTable, LogTableRow } from "@/components/logs/logs-table";
import {
  isMessageInput,
  isMessageItem,
  isFunctionCallItem,
  isWebSearchCallItem,
  MessageItem,
  FunctionCallItem,
  WebSearchCallItem,
} from "./utils/itemTypeGuards";

interface ResponsesTableProps {
  data: OpenAIResponse[];
  isLoading: boolean;
  error: Error | null;
}

function getInputText(response: OpenAIResponse): string {
  // Extract text from the first input message using type guard
  const firstInput = response.input.find(isMessageInput);
  if (firstInput) {
    return extractInputContent(firstInput);
  }
  return "";
}

function getOutputText(response: OpenAIResponse): string {
  // First try to find a message output using type guard
  const firstMessage = response.output.find((item) =>
    isMessageItem(item as any),
  );
  if (firstMessage) {
    const content = extractMessageContent(firstMessage as MessageItem);
    if (content) {
      return content;
    }
  }

  // If no message output, look for tool calls using type guards
  const functionCall = response.output.find((item) =>
    isFunctionCallItem(item as any),
  );
  if (functionCall) {
    return formatFunctionCall(functionCall as FunctionCallItem);
  }

  const webSearchCall = response.output.find((item) =>
    isWebSearchCallItem(item as any),
  );
  if (webSearchCall) {
    return formatWebSearchCall(webSearchCall as WebSearchCallItem);
  }

  return JSON.stringify(response.output);
}

function extractInputContent(
  inputItem: ResponseInput & { type: "message" },
): string {
  if (!inputItem.content) {
    return "";
  }

  if (typeof inputItem.content === "string") {
    return inputItem.content;
  } else if (Array.isArray(inputItem.content)) {
    const textContent = inputItem.content.find(
      (c: ResponseInputMessageContent) =>
        c.type === "input_text" || c.type === "output_text",
    );
    return textContent?.text || "";
  }
  return "";
}

function extractMessageContent(messageItem: MessageItem): string {
  if (typeof messageItem.content === "string") {
    return messageItem.content;
  } else if (Array.isArray(messageItem.content)) {
    const textContent = messageItem.content.find(
      (c: ResponseInputMessageContent) =>
        c.type === "input_text" || c.type === "output_text",
    );
    return textContent?.text || "";
  }
  return "";
}

function formatFunctionCall(functionCall: FunctionCallItem): string {
  const args = functionCall.arguments || "{}";
  const name = functionCall.name || "unknown";
  return `${name}(${args})`;
}

function formatWebSearchCall(webSearchCall: WebSearchCallItem): string {
  return `web_search_call(status: ${webSearchCall.status})`;
}

function formatResponseToRow(response: OpenAIResponse): LogTableRow {
  return {
    id: response.id,
    input: getInputText(response),
    output: getOutputText(response),
    model: response.model,
    createdTime: new Date(response.created_at * 1000).toLocaleString(),
    detailPath: `/logs/responses/${response.id}`,
  };
}

export function ResponsesTable({
  data,
  isLoading,
  error,
}: ResponsesTableProps) {
  const formattedData = data.map(formatResponseToRow);

  return (
    <LogsTable
      data={formattedData}
      isLoading={isLoading}
      error={error}
      caption="A list of your recent responses."
      emptyMessage="No responses found."
    />
  );
}
