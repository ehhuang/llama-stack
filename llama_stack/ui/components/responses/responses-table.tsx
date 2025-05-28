"use client";

import { OpenAIResponse } from "@/lib/types";
import { LogsTable, LogTableRow } from "@/components/logs/logs-table";

interface ResponsesTableProps {
  data: OpenAIResponse[];
  isLoading: boolean;
  error: Error | null;
}

function getInputText(response: OpenAIResponse): string {
  // Extract text from the first input message
  const firstInput = response.input.find((input) => input.type === "message");
  if (firstInput && typeof firstInput.content === "string") {
    return firstInput.content;
  } else if (firstInput && Array.isArray(firstInput.content)) {
    const textContent = firstInput.content.find((c) => c.type === "input_text");
    return textContent?.text || "";
  }
  return "";
}

function getOutputText(response: OpenAIResponse): string {
  // First try to find a message output
  const firstMessage = response.output.find(
    (output) => output.type === "message",
  );
  if (firstMessage && "content" in firstMessage) {
    if (typeof firstMessage.content === "string") {
      return firstMessage.content;
    } else if (Array.isArray(firstMessage.content)) {
      const textContent = firstMessage.content.find(
        (c) => c.type === "output_text",
      );
      if (textContent?.text) {
        return textContent.text;
      }
    }
  }

  // If no message output, look for tool calls
  const toolCall = response.output.find(
    (output) =>
      output.type === "function_call" || output.type === "web_search_call",
  );
  if (toolCall) {
    if (toolCall.type === "function_call" && "name" in toolCall) {
      const args =
        "arguments" in toolCall && toolCall.arguments
          ? toolCall.arguments
          : "{}";
      return `${toolCall.name}(${args})`;
    } else if (toolCall.type === "web_search_call") {
      return `web_search_call(status: ${toolCall.status})`;
    } else {
      return JSON.stringify(toolCall);
    }
  }

  return JSON.stringify(response.output);
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
