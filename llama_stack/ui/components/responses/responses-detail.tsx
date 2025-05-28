"use client";

import { OpenAIResponse, InputItemListResponse } from "@/lib/types";
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

function ItemDisplay({
  item,
  index,
  keyPrefix,
  defaultRole = "unknown",
}: {
  item: unknown;
  index: number;
  keyPrefix: string;
  defaultRole?: string;
}) {
  // Handle different types of items (input or output)
  const itemData = item as Record<string, unknown>;

  if (itemData.type === "message" && "content" in itemData) {
    let content = "";
    if (typeof itemData.content === "string") {
      content = itemData.content;
    } else if (Array.isArray(itemData.content)) {
      content = itemData.content
        .map((c: unknown) => {
          const contentItem = c as Record<string, unknown>;
          return contentItem.type === "input_text" ||
            contentItem.type === "output_text"
            ? contentItem.text
            : JSON.stringify(c);
        })
        .join(" ");
    }

    const role = (itemData.role as string) || defaultRole;
    const label = role.charAt(0).toUpperCase() + role.slice(1);

    return (
      <MessageBlock
        key={`${keyPrefix}-${index}`}
        label={label}
        content={content}
      />
    );
  } else if (itemData.type === "function_call" && "name" in itemData) {
    // Format function call like chat completion details: functionName(arguments)
    const name = (itemData.name as string) || "unknown";
    const args =
      "arguments" in itemData && itemData.arguments ? itemData.arguments : "{}";
    const formattedFunctionCall = `${name}(${args})`;

    return (
      <MessageBlock
        key={`${keyPrefix}-${index}`}
        label="Function Call"
        content={<ToolCallBlock>{formattedFunctionCall}</ToolCallBlock>}
      />
    );
  } else if (itemData.type === "web_search_call") {
    // Format web search call similarly - just show the type and status if available
    const formattedWebSearch = `web_search_call(status: ${itemData.status})`;

    return (
      <MessageBlock
        key={`${keyPrefix}-${index}`}
        label="Function Call"
        labelDetail="(Web Search)"
        content={<ToolCallBlock>{formattedWebSearch}</ToolCallBlock>}
      />
    );
  } else {
    // Handle other types like function calls, tool outputs, etc.
    const content = itemData.content
      ? typeof itemData.content === "string"
        ? itemData.content
        : JSON.stringify(itemData.content, null, 2)
      : JSON.stringify(itemData, null, 2);

    const label = keyPrefix === "input" ? "Input" : "Output";

    return (
      <MessageBlock
        key={`${keyPrefix}-${index}`}
        label={label}
        labelDetail={`(${itemData.type})`}
        content={<ToolCallBlock>{content}</ToolCallBlock>}
      />
    );
  }
}

function GroupedItemsDisplay({
  items,
  keyPrefix,
  defaultRole = "unknown",
}: {
  items: unknown[];
  keyPrefix: string;
  defaultRole?: string;
}) {
  const groupedItems: React.JSX.Element[] = [];
  const processedIndices = new Set<number>();

  const callIdToIndices = new Map<string, number[]>();

  for (let i = 0; i < items.length; i++) {
    const item = items[i] as Record<string, unknown>;
    if (
      item.type === "function_call_output" &&
      item.call_id &&
      typeof item.call_id === "string"
    ) {
      if (!callIdToIndices.has(item.call_id)) {
        callIdToIndices.set(item.call_id, []);
      }
      callIdToIndices.get(item.call_id)!.push(i);
    }
  }

  for (let i = 0; i < items.length; i++) {
    if (processedIndices.has(i)) {
      continue;
    }

    const currentItem = items[i] as Record<string, unknown>;

    if (
      currentItem.type === "function_call" &&
      "name" in currentItem &&
      "call_id" in currentItem
    ) {
      const functionCallId = currentItem.call_id as string;
      let outputIndex = -1;
      let outputItem: Record<string, unknown> | null = null;

      const relatedIndices = callIdToIndices.get(functionCallId) || [];
      for (const idx of relatedIndices) {
        if (idx === i || processedIndices.has(idx)) continue;

        const potentialOutput = items[idx] as Record<string, unknown>;
        if (potentialOutput.type === "function_call_output") {
          outputIndex = idx;
          outputItem = potentialOutput;
          break;
        }
      }

      if (outputItem && outputIndex !== -1) {
        // Group function call with its function_call_output
        const name = (currentItem.name as string) || "unknown";
        const args =
          "arguments" in currentItem && currentItem.arguments
            ? currentItem.arguments
            : "{}";

        // Extract the output content from function_call_output
        let outputContent = "";
        if (outputItem.output) {
          outputContent =
            typeof outputItem.output === "string"
              ? outputItem.output
              : JSON.stringify(outputItem.output);
        } else {
          outputContent = JSON.stringify(outputItem, null, 2);
        }

        const functionCallContent = (
          <div>
            <div className="mb-2">
              <span className="text-sm text-gray-600">Arguments</span>
              <ToolCallBlock>{`${name}(${args})`}</ToolCallBlock>
            </div>
            <div>
              <span className="text-sm text-gray-600">Output</span>
              <ToolCallBlock>{outputContent}</ToolCallBlock>
            </div>
          </div>
        );

        groupedItems.push(
          <MessageBlock
            key={`${keyPrefix}-${i}`}
            label="Function Call"
            content={functionCallContent}
          />,
        );

        // Mark both items as processed
        processedIndices.add(i);
        processedIndices.add(outputIndex);
      } else {
        // No matching function_call_output found, render function call alone
        groupedItems.push(
          <ItemDisplay
            key={`${keyPrefix}-${i}`}
            item={currentItem}
            index={i}
            keyPrefix={keyPrefix}
            defaultRole={defaultRole}
          />,
        );
        processedIndices.add(i);
      }
    } else {
      // Not a function call, render normally (including message items)
      groupedItems.push(
        <ItemDisplay
          key={`${keyPrefix}-${i}`}
          item={currentItem}
          index={i}
          keyPrefix={keyPrefix}
          defaultRole={defaultRole}
        />,
      );
      processedIndices.add(i);
    }
  }

  return <>{groupedItems}</>;
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
          <CardTitle>Input</CardTitle>
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
              return GroupedItemsDisplay({
                items: dataToDisplay,
                keyPrefix: "input",
                defaultRole: "unknown",
              });
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
            GroupedItemsDisplay({
              items: response.output,
              keyPrefix: "output",
              defaultRole: "assistant",
            })
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
