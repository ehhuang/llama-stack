import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge"; // Import Badge for status
import { ChatCompletionLogEntrySummary } from "@/types/logs";
import { Skeleton } from "@/components/ui/skeleton"; // Import Skeleton for loading state

interface ChatCompletionLogTableProps {
  chatCompletionLogs: ChatCompletionLogEntrySummary[];
  isLoading: boolean;
  error: Error | null;
  onRowClick?: (logId: string) => void; // Add optional click handler prop
  // Add other props as needed, e.g., for pagination later
}

// Helper function to format timestamp
const formatTimestamp = (isoString: string) => {
  if (!isoString) return "";
  try {
    const date = new Date(isoString);
    // Example format: "6/21/2024, 3:05:10 PM" - adjust locale/options as needed
    return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
  } catch (e) {
    console.error("Error formatting date:", e);
    return isoString; // Fallback to raw string
  }
};

export function ChatCompletionLogTable({
  chatCompletionLogs,
  isLoading,
  error,
  onRowClick, // Destructure the handler
}: ChatCompletionLogTableProps) {
  const tableColumns = [
    { key: "inputPreview", label: "Input" },
    { key: "outputPreview", label: "Output" },
    { key: "model", label: "Model" },
    { key: "status", label: "Status" },
    { key: "timestamp", label: "Created" },
  ];

  const renderCellContent = (
    chatCompletionLog: ChatCompletionLogEntrySummary,
    columnKey: string,
  ) => {
    switch (columnKey) {
      case "timestamp":
        return formatTimestamp(chatCompletionLog.timestamp);
      case "status":
        return (
          <Badge variant={chatCompletionLog.status === "Success" ? "default" : "destructive"}>
            {chatCompletionLog.status}
          </Badge>
        );
      case "model":
        return chatCompletionLog.model;
      case "inputPreview":
        return <span className="block max-w-xs truncate">{chatCompletionLog.inputPreview}</span>;
      case "outputPreview":
        return <span className="block max-w-xs truncate">{chatCompletionLog.outputPreview}</span>;
      case "duration":
        return chatCompletionLog.durationFormatted ?? "-"; // Display formatted duration or dash
      default:
        return null;
    }
  };

  // Prepare table body content based on state
  let tableBodyContent;
  if (isLoading) {
    // Render skeleton rows matching the number of columns
    tableBodyContent = [...Array(3)].map((_, index) => (
      <TableRow key={`skeleton-${index}`}>
        {tableColumns.map((col) => (
          <TableCell key={`${col.key}-skeleton-${index}`}>
            <Skeleton data-testid="skeleton" className="h-4 w-full" />
          </TableCell>
        ))}
      </TableRow>
    ));
  } else if (error) {
    tableBodyContent = (
      <TableRow>
        <TableCell colSpan={tableColumns.length} className="h-24 text-center text-red-500">
          Error loading logs: {error.message}
        </TableCell>
      </TableRow>
    );
  } else if (!chatCompletionLogs || chatCompletionLogs.length === 0) {
    tableBodyContent = (
      <TableRow>
        <TableCell colSpan={tableColumns.length} className="h-24 text-center text-gray-500">
          No logs found.
        </TableCell>
      </TableRow>
    );
  } else {
    tableBodyContent = chatCompletionLogs.map((log) => (
      <TableRow
        key={log.id}
        onClick={() => onRowClick?.(log.id)} // Add onClick handler
        className={onRowClick ? "cursor-pointer hover:bg-muted/50" : ""} // Add cursor and hover style if clickable
      >
        {tableColumns.map((col) => (
          <TableCell key={`${log.id}-${col.key}`}>
            {renderCellContent(log, col.key)}
          </TableCell>
        ))}
      </TableRow>
    ));
  }

  // Render Table Structure - Always render headers
  return (
    <Table>
      <TableCaption>A list of recent chat completions requests.</TableCaption>
      <TableHeader>
        <TableRow>
          {tableColumns.map((col) => (
            <TableHead key={col.key}>{col.label}</TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>{tableBodyContent}</TableBody>
    </Table>
  );
} 