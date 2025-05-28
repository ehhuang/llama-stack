import {
  isMessageItem,
  isFunctionCallItem,
  isWebSearchCallItem,
  AnyResponseItem,
} from "../utils/itemTypeGuards";
import { MessageItemComponent } from "./MessageItem";
import { FunctionCallItemComponent } from "./FunctionCallItem";
import { WebSearchItemComponent } from "./WebSearchItem";
import { GenericItemComponent } from "./GenericItem";

interface ItemRendererProps {
  item: AnyResponseItem;
  index: number;
  keyPrefix: string;
  defaultRole?: string;
}

export function ItemRenderer({
  item,
  index,
  keyPrefix,
  defaultRole = "unknown",
}: ItemRendererProps) {
  if (isMessageItem(item)) {
    return (
      <MessageItemComponent
        item={item}
        index={index}
        keyPrefix={keyPrefix}
        defaultRole={defaultRole}
      />
    );
  }

  if (isFunctionCallItem(item)) {
    return (
      <FunctionCallItemComponent
        item={item}
        index={index}
        keyPrefix={keyPrefix}
      />
    );
  }

  if (isWebSearchCallItem(item)) {
    return (
      <WebSearchItemComponent item={item} index={index} keyPrefix={keyPrefix} />
    );
  }

  // Fallback to generic item for unknown types
  return (
    <GenericItemComponent
      item={item as any}
      index={index}
      keyPrefix={keyPrefix}
    />
  );
}
