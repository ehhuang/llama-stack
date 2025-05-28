import { useFunctionCallGrouping } from "../hooks/useFunctionCallGrouping";
import { ItemRenderer } from "../items/ItemRenderer";
import { GroupedFunctionCallItemComponent } from "../items/GroupedFunctionCallItem";
import {
  isFunctionCallItem,
  isFunctionCallOutputItem,
  AnyResponseItem,
} from "../utils/itemTypeGuards";

interface GroupedItemsDisplayProps {
  items: AnyResponseItem[];
  keyPrefix: string;
  defaultRole?: string;
}

export function GroupedItemsDisplay({
  items,
  keyPrefix,
  defaultRole = "unknown",
}: GroupedItemsDisplayProps) {
  const groupedItems = useFunctionCallGrouping(items);

  return (
    <>
      {groupedItems.map((groupedItem) => {
        // If this is a function call with an output, render the grouped component
        if (
          groupedItem.outputItem &&
          isFunctionCallItem(groupedItem.item) &&
          isFunctionCallOutputItem(groupedItem.outputItem)
        ) {
          return (
            <GroupedFunctionCallItemComponent
              key={`${keyPrefix}-${groupedItem.index}`}
              functionCall={groupedItem.item}
              output={groupedItem.outputItem}
              index={groupedItem.index}
              keyPrefix={keyPrefix}
            />
          );
        }

        // Otherwise, render the individual item
        return (
          <ItemRenderer
            key={`${keyPrefix}-${groupedItem.index}`}
            item={groupedItem.item}
            index={groupedItem.index}
            keyPrefix={keyPrefix}
            defaultRole={defaultRole}
          />
        );
      })}
    </>
  );
}
