/**
 * Type guards for different item types in responses
 * Updated to work with actual API types from lib/types.ts
 */

import type {
  ResponseInput,
  ResponseOutput,
  ResponseMessage,
  ResponseToolCall,
} from "@/lib/types";

export interface BaseItem {
  type: string;
  [key: string]: unknown;
}

// Use the actual API types instead of creating new ones
export type MessageItem = ResponseMessage;
export type FunctionCallItem = ResponseToolCall & { type: "function_call" };
export type WebSearchCallItem = ResponseToolCall & { type: "web_search_call" };
export type FunctionCallOutputItem = BaseItem & {
  type: "function_call_output";
  call_id: string;
  output?: string | object;
};

// Union type for all possible items we might encounter
export type AnyResponseItem =
  | ResponseInput
  | ResponseOutput
  | FunctionCallOutputItem;

// Type guards for ResponseInput (used in input arrays)
export function isMessageInput(
  item: ResponseInput,
): item is ResponseInput & { type: "message" } {
  return item.type === "message";
}

// Unified type guards that work with AnyResponseItem (covers all use cases)
export function isMessageItem(item: AnyResponseItem): item is MessageItem {
  return item.type === "message" && "content" in item;
}

export function isFunctionCallItem(
  item: AnyResponseItem,
): item is FunctionCallItem {
  return item.type === "function_call" && "name" in item;
}

export function isWebSearchCallItem(
  item: AnyResponseItem,
): item is WebSearchCallItem {
  return item.type === "web_search_call";
}

export function isFunctionCallOutputItem(
  item: AnyResponseItem,
): item is FunctionCallOutputItem {
  return (
    item.type === "function_call_output" &&
    "call_id" in item &&
    typeof (item as any).call_id === "string"
  );
}
