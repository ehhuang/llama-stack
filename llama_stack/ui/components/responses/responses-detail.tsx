"use client";

import {
  OpenAIResponse,
  ResponseOutput,
  ResponseMessage,
  InputItemListResponse,
} from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  MessageBlock,
  ToolCallBlock,
} from "@/components/ui/message-components";
import {
  DetailLoadingView,
  DetailErrorView,
  DetailNotFoundView,
  DetailLayout,
  PropertiesCard,
  PropertyItem,
} from "@/components/ui/detail-layout";

function ResponseInputDisplay({
  input,
  index,
}: {
  input: unknown;
  index: number;
}) {
  // Handle different types of input
  const inputData = input as Record<string, unknown>;
  if (inputData.type === "message") {
    let content = "";
    if (typeof inputData.content === "string") {
      content = inputData.content;
    } else if (Array.isArray(inputData.content)) {
      content = inputData.content
        .map((c: unknown) => {
          const contentItem = c as Record<string, unknown>;
          return contentItem.type === "input_text" ||
            contentItem.type === "output_text"
            ? contentItem.text
            : JSON.stringify(c);
        })
        .join(" ");
    }

    const role = (inputData.role as string) || "unknown";
    const label = role.charAt(0).toUpperCase() + role.slice(1);

    return (
      <MessageBlock key={`input-${index}`} label={label} content={content} />
    );
  } else {
    // Handle other input types like function calls, tool outputs, etc.
    const content = inputData.content
      ? typeof inputData.content === "string"
        ? inputData.content
        : JSON.stringify(inputData.content, null, 2)
      : JSON.stringify(inputData, null, 2);

    return (
      <MessageBlock
        key={`input-${index}`}
        label="Input"
        labelDetail={`(${inputData.type})`}
        content={<ToolCallBlock>{content}</ToolCallBlock>}
      />
    );
  }
}

function ResponseOutputDisplay({
  output,
  index,
}: {
  output: ResponseOutput;
  index: number;
}) {
  if (output.type === "message" && "content" in output) {
    const message = output as ResponseMessage;
    let content = "";

    if (typeof message.content === "string") {
      content = message.content;
    } else if (Array.isArray(message.content)) {
      content = message.content
        .map((c: unknown) => {
          const contentItem = c as Record<string, unknown>;
          return contentItem.type === "output_text" ||
            contentItem.type === "input_text"
            ? contentItem.text
            : JSON.stringify(c);
        })
        .join(" ");
    }

    const role = message.role || "assistant";
    const label = role.charAt(0).toUpperCase() + role.slice(1);

    return (
      <MessageBlock key={`output-${index}`} label={label} content={content} />
    );
  } else if (output.type === "function_call" && "name" in output) {
    // Format tool call like chat completion details: functionName(arguments)
    const name = output.name || "unknown";
    const args =
      "arguments" in output && output.arguments ? output.arguments : "{}";
    const formattedToolCall = `${name}(${args})`;

    return (
      <MessageBlock
        key={`output-${index}`}
        label="Tool Call"
        content={<ToolCallBlock>{formattedToolCall}</ToolCallBlock>}
      />
    );
  } else if (output.type === "web_search_call") {
    // Format web search call similarly - just show the type and status if available
    const formattedWebSearch = `web_search_call(status: ${output.status})`;

    return (
      <MessageBlock
        key={`output-${index}`}
        label="Tool Call"
        labelDetail="(Web Search)"
        content={<ToolCallBlock>{formattedWebSearch}</ToolCallBlock>}
      />
    );
  }

  // Fallback for unknown output types
  return (
    <MessageBlock
      key={`output-${index}`}
      label="Output"
      labelDetail={`(${output.type})`}
      content={<ToolCallBlock>{JSON.stringify(output, null, 2)}</ToolCallBlock>}
    />
  );
}

interface ResponseDetailViewProps {
  response: OpenAIResponse | null;
  inputItems: InputItemListResponse | null;
  isLoading: boolean;
  isLoadingInputItems: boolean;
  error: Error | null;
  inputItemsError: Error | null;
  id: string;
}

export function ResponseDetailView({
  response,
  inputItems,
  isLoading,
  isLoadingInputItems,
  error,
  inputItemsError,
  id,
}: ResponseDetailViewProps) {
  const title = "Responses Details";

  if (error) {
    return <DetailErrorView title={title} id={id} error={error} />;
  }

  if (isLoading) {
    return <DetailLoadingView title={title} />;
  }

  if (!response) {
    return <DetailNotFoundView title={title} id={id} />;
  }

  // Main content cards
  const mainContent = (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Input Items</CardTitle>
        </CardHeader>
        <CardContent>
          {/* Show loading state for input items */}
          {isLoadingInputItems ? (
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
            </div>
          ) : inputItemsError ? (
            <div className="text-red-500 text-sm">
              Error loading input items: {inputItemsError.message}
              <br />
              <span className="text-gray-500 text-xs">
                Falling back to response input data.
              </span>
            </div>
          ) : null}

          {/* Display input items if available, otherwise fall back to response.input */}
          {(() => {
            const dataToDisplay =
              inputItems?.data && inputItems.data.length > 0
                ? inputItems.data
                : response.input;

            if (dataToDisplay && dataToDisplay.length > 0) {
              return dataToDisplay.map((input, index) => (
                <ResponseInputDisplay
                  key={`input-${index}`}
                  input={input}
                  index={index}
                />
              ));
            } else {
              return (
                <p className="text-gray-500 italic text-sm">
                  No input data available.
                </p>
              );
            }
          })()}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Output</CardTitle>
        </CardHeader>
        <CardContent>
          {response.output?.length > 0 ? (
            response.output.map((output, index) => (
              <ResponseOutputDisplay
                key={`output-${index}`}
                output={output}
                index={index}
              />
            ))
          ) : (
            <p className="text-gray-500 italic text-sm">
              No output data available.
            </p>
          )}
        </CardContent>
      </Card>
    </>
  );

  // Properties sidebar
  const sidebar = (
    <PropertiesCard>
      <PropertyItem
        label="Created"
        value={new Date(response.created_at * 1000).toLocaleString()}
      />
      <PropertyItem label="ID" value={response.id} />
      <PropertyItem label="Model" value={response.model} />
      <PropertyItem label="Status" value={response.status} hasBorder />
      {response.temperature && (
        <PropertyItem
          label="Temperature"
          value={response.temperature}
          hasBorder
        />
      )}
      {response.top_p && <PropertyItem label="Top P" value={response.top_p} />}
      {response.parallel_tool_calls && (
        <PropertyItem
          label="Parallel Tool Calls"
          value={response.parallel_tool_calls ? "Yes" : "No"}
        />
      )}
      {response.previous_response_id && (
        <PropertyItem
          label="Previous Response ID"
          value={
            <span className="text-xs">{response.previous_response_id}</span>
          }
          hasBorder
        />
      )}
      {response.error && (
        <PropertyItem
          label="Error"
          value={
            <span className="text-red-900 font-medium">
              {response.error.code}: {response.error.message}
            </span>
          }
          className="pt-1 mt-1 border-t border-red-200"
        />
      )}
    </PropertiesCard>
  );

  return (
    <DetailLayout title={title} mainContent={mainContent} sidebar={sidebar} />
  );
}
