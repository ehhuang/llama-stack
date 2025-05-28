/**
 * Type guards for different item types in responses
 */

export interface BaseItem {
  type: string;
  [key: string]: unknown;
}

export interface MessageItem extends BaseItem {
  type: "message";
  content:
    | string
    | Array<{ type: string; text?: string; [key: string]: unknown }>;
  role?: string;
}

export interface FunctionCallItem extends BaseItem {
  type: "function_call";
  name: string;
  arguments?: string;
  call_id?: string;
}

export interface FunctionCallOutputItem extends BaseItem {
  type: "function_call_output";
  call_id: string;
  output?: string | object;
}

export interface WebSearchCallItem extends BaseItem {
  type: "web_search_call";
  status?: string;
}

export function isMessageItem(item: unknown): item is MessageItem {
  const itemData = item as Record<string, unknown>;
  return itemData.type === "message" && "content" in itemData;
}

export function isFunctionCallItem(item: unknown): item is FunctionCallItem {
  const itemData = item as Record<string, unknown>;
  return itemData.type === "function_call" && "name" in itemData;
}

export function isFunctionCallOutputItem(
  item: unknown,
): item is FunctionCallOutputItem {
  const itemData = item as Record<string, unknown>;
  return (
    itemData.type === "function_call_output" &&
    "call_id" in itemData &&
    typeof itemData.call_id === "string"
  );
}

export function isWebSearchCallItem(item: unknown): item is WebSearchCallItem {
  const itemData = item as Record<string, unknown>;
  return itemData.type === "web_search_call";
}
