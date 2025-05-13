"use client";

import React, { useState, useEffect } from 'react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
  SheetClose,
} from "@/components/ui/sheet";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Toaster, toast } from "sonner";
import { logService } from "@/mocks/logService";
import { fetchChatCompletionDetailFromAPI } from "@/services/chatLogService";
import type { ChatCompletionLogEntryDetail, LogMessage } from "@/types/logs";
import { Copy, Check } from "lucide-react";

// --- Helper Components ---

// Helper to format and display a single key-value pair
function DetailItem({ label, value }: { label: string; value: React.ReactNode }) {
  if (value === undefined || value === null || value === '') return null;
  return (
    <div className="grid grid-cols-3 gap-2 text-sm">
      <dt className="text-muted-foreground font-medium col-span-1">{label}</dt>
      <dd className="col-span-2 break-words">{value}</dd>
    </div>
  );
}

// Reusable Copy Button
function CopyButton({ textToCopy, size = 16 }: { textToCopy: string | undefined, size?: number }) {
  const [copied, setCopied] = useState(false);

  const handleCopyClick = () => {
    if (!textToCopy) return;
    navigator.clipboard.writeText(textToCopy).then(() => {
      setCopied(true);
      toast.success("Copied to clipboard!");
      setTimeout(() => setCopied(false), 1500);
    }).catch(err => {
      console.error("Failed to copy:", err);
      toast.error("Copy Failed", {
        description: "Could not copy text to clipboard.",
      });
    });
  };

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={handleCopyClick}
      className="h-6 w-6 ml-1" // Smaller size
      aria-label="Copy to clipboard"
    >
      {copied ? <Check size={size} /> : <Copy size={size} />}
    </Button>
  );
}

// Helper to display individual messages
function LogMessageDisplay({ message }: { message: LogMessage }) {
  const getRoleBadgeVariant = (role: LogMessage['role']) => {
    switch (role) {
      case 'user': return 'secondary';
      case 'assistant': return 'default';
      case 'system': return 'outline';
      case 'tool': return 'destructive';
      default: return 'secondary';
    }
  };

  return (
    <div className="mb-4 p-3 border rounded-md space-y-2">
      <div className="flex justify-between items-center">
        <Badge variant={getRoleBadgeVariant(message.role)} className="capitalize">
          {message.role}
          {message.name && ` (${message.name})`}
        </Badge>
        {message.tool_call_id && (
          <span className="text-xs text-muted-foreground">Tool Call ID: {message.tool_call_id.substring(0, 8)}...</span>
        )}
      </div>
      {message.content && (
        <pre className="p-2 bg-muted rounded-md text-sm whitespace-pre-wrap break-words">
          {typeof message.content === 'string' ? message.content : JSON.stringify(message.content, null, 2)}
        </pre>
      )}
      {message.tool_calls && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-muted-foreground">Tool Calls:</p>
          {message.tool_calls.map((call) => (
            <pre key={call.id} className="p-2 bg-muted rounded-md text-sm whitespace-pre-wrap break-words">
              {JSON.stringify(call.function, null, 2)}
            </pre>
          ))}
        </div>
      )}
    </div>
  );
}

// --- Main Component ---

interface ChatCompletionLogDetailViewProps {
  logId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export function ChatCompletionLogDetailView({
  logId,
  isOpen,
  onClose,
}: ChatCompletionLogDetailViewProps) {
  const [logDetail, setLogDetail] = useState<ChatCompletionLogEntryDetail | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (isOpen && logId) {
      const fetchDetail = async () => {
        setIsLoading(true);
        setError(null);
        setLogDetail(null);
        try {
          let detail: ChatCompletionLogEntryDetail | null = null;
          if (process.env.NEXT_PUBLIC_USE_MOCK_API === "true") {
            detail = await logService.fetchChatCompletionDetail(logId);
          } else {
            detail = await fetchChatCompletionDetailFromAPI(logId);
          }
          if (detail) {
            setLogDetail(detail);
          } else {
            setError(new Error("Log not found."));
          }
        } catch (err) {
          console.error("Failed to fetch log detail:", err);
          setError(err instanceof Error ? err : new Error("Failed to load details"));
        } finally {
          setIsLoading(false);
        }
      };
      fetchDetail();
    } else {
      setLogDetail(null);
      setIsLoading(false);
      setError(null);
    }
  }, [isOpen, logId]);

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      onClose();
    }
  };

  const renderLoadingState = () => (
    <div className="space-y-4">
      <Skeleton className="h-8 w-1/2 mb-4" />
      <Skeleton className="h-4 w-3/4 mb-2" />
      <Skeleton className="h-4 w-full mb-2" />
      <Skeleton className="h-4 w-2/3 mb-4" />
      <Card>
        <CardHeader><Skeleton className="h-6 w-1/4" /></CardHeader>
        <CardContent className="space-y-2">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
        </CardContent>
      </Card>
      <Card>
        <CardHeader><Skeleton className="h-6 w-1/4" /></CardHeader>
        <CardContent><Skeleton className="h-20 w-full" /></CardContent>
      </Card>
    </div>
  );

  const renderErrorState = () => (
    <div className="text-red-500 p-4 border border-red-200 rounded-md bg-red-50">
      Error: {error?.message || 'Unknown error'}
    </div>
  );

  const renderEmptyState = () => (
    <div className="text-muted-foreground p-4 text-center">
      {logId ? 'Log details could not be loaded or found.' : 'Select a log entry to view details.'}
    </div>
  );

  return (
    <Sheet open={isOpen} onOpenChange={handleOpenChange}>
      <SheetContent className="sm:max-w-2xl w-full overflow-y-auto flex flex-col">
        <SheetHeader>
          <SheetTitle>Log Details</SheetTitle>
          {logId && (
             <SheetDescription className="flex items-center">
               ID: {logId}
               <CopyButton textToCopy={logId} size={14} />
             </SheetDescription>
          )}
        </SheetHeader>

        <div className="py-4 space-y-4 flex-grow"> {/* Content area */}
          {isLoading && renderLoadingState()}
          {error && renderErrorState()}
          {!isLoading && !error && !logDetail && renderEmptyState()}
          {!isLoading && !error && logDetail && (
            <div className="space-y-4">
              {/* --- Metadata Card --- */}
              <Card>
                <CardHeader>
                  <CardTitle>Metadata</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <DetailItem label="Timestamp" value={logDetail.timestamp ? new Date(logDetail.timestamp).toLocaleString() : '-'} />
                  <DetailItem label="Status" value={<Badge variant={logDetail.status === "Success" ? "default" : "destructive"}>{logDetail.status}</Badge>} />
                  <DetailItem label="Model" value={logDetail.model || '-'} />
                  <DetailItem label="Duration" value={typeof logDetail.durationMs === 'number' ? `${(logDetail.durationMs / 1000).toFixed(2)}s` : '-'} />
                </CardContent>
              </Card>

              {/* --- Usage & Cost Card (Optional) --- */}
              {(logDetail.usage || typeof logDetail.cost === 'number') && (
                <Card>
                  <CardHeader>
                    <CardTitle>Usage & Cost</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <DetailItem label="Prompt Tokens" value={logDetail.usage?.prompt_tokens} />
                    <DetailItem label="Completion Tokens" value={logDetail.usage?.completion_tokens} />
                    <DetailItem label="Total Tokens" value={logDetail.usage?.total_tokens} />
                    <DetailItem label="Cost (USD)" value={typeof logDetail.cost === 'number' ? `$${logDetail.cost.toFixed(6)}` : undefined} />
                  </CardContent>
                </Card>
              )}

              {/* --- Error Details Card (Optional) --- */}
              {logDetail.status === 'Error' && logDetail.error && (
                <Card className="border-destructive">
                  <CardHeader>
                    <CardTitle className="text-destructive">Error Details</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <DetailItem label="Message" value={logDetail.error.message} />
                    <DetailItem label="Type" value={logDetail.error.type} />
                    <DetailItem label="Code" value={logDetail.error.code} />
                  </CardContent>
                </Card>
              )}

              {/* --- Messages Accordion --- */}
              <Accordion type="single" collapsible className="w-full" defaultValue="messages">
                <AccordionItem value="messages">
                  <AccordionTrigger className="text-lg font-semibold">Messages</AccordionTrigger>
                  <AccordionContent>
                    {Array.isArray(logDetail.messages) && logDetail.messages.length > 0 ? (
                      logDetail.messages.map((msg, index) => (
                        <div key={index} className="relative group">
                          <LogMessageDisplay message={msg} />
                          {(typeof msg.content === 'string' && msg.content) && (
                             <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                <CopyButton textToCopy={msg.content} size={14} />
                             </div>
                          )}
                        </div>
                      ))
                    ) : (
                      <div className="text-muted-foreground text-sm p-2">No messages available.</div>
                    )}
                  </AccordionContent>
                </AccordionItem>
              </Accordion>

               {/* --- Tags Card (Optional) --- */}
              {logDetail.tags && Object.keys(logDetail.tags).length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Tags</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {Object.entries(logDetail.tags).map(([key, value]) => (
                       <DetailItem key={key} label={key} value={value} />
                    ))}
                  </CardContent>
                </Card>
              )}

            </div>
          )}
        </div>

        <SheetFooter data-testid="sheet-footer">
          <SheetClose asChild>
            <Button variant="outline">Close</Button>
          </SheetClose>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
} 