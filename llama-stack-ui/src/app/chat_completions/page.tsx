"use client"; // Required for hooks like useState, useEffect

import React, { useState, useEffect } from 'react';
import { ChatCompletionLogTable } from '@/components/logs/chat_completions/ChatCompletionLogTable';
import { ChatCompletionLogDetailView } from '@/components/logs/chat_completions/ChatCompletionLogDetailView';
import { logService } from '@/mocks/logService';
import { fetchChatCompletionListFromAPI } from '@/services/chatLogService';
import type { ChatCompletionLogEntrySummary } from '@/types/logs';

export default function Home() {
  const [chatCompletionLogs, setChatCompletionLogs] = useState<ChatCompletionLogEntrySummary[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  // State for Detail View
  const [selectedLogId, setSelectedLogId] = useState<string | null>(null);
  const [isDetailViewOpen, setIsDetailViewOpen] = useState<boolean>(false);

  useEffect(() => {
    const loadLogs = async () => {
      setIsLoading(true);
      setError(null);
      try {
        let response;
        if (process.env.NEXT_PUBLIC_USE_MOCK_API === 'true') {
          response = await logService.fetchChatCompletionList({});
        } else {
          response = await fetchChatCompletionListFromAPI();
        }
        setChatCompletionLogs(response.logs);
      } catch (err) {
        console.error("Failed to fetch logs:", err);
        setError(err instanceof Error ? err : new Error('Failed to load logs'));
      } finally {
        setIsLoading(false);
      }
    };

    loadLogs();
  }, []); // Empty dependency array means this runs once on mount

  // Handler to open detail view
  const handleLogRowClick = (logId: string) => {
    setSelectedLogId(logId);
    setIsDetailViewOpen(true);
  };

  // Handler to close detail view
  const handleDetailViewClose = () => {
    setIsDetailViewOpen(false);
    setSelectedLogId(null); // Clear selection on close
  };

  return (
    <main className="container mx-auto py-10">
      <h1 className="text-2xl font-bold mb-6">Chat Completions</h1>
      <ChatCompletionLogTable
        chatCompletionLogs={chatCompletionLogs}
        isLoading={isLoading}
        error={error}
        onRowClick={handleLogRowClick}
      />
      <ChatCompletionLogDetailView
        logId={selectedLogId}
        isOpen={isDetailViewOpen}
        onClose={handleDetailViewClose}
      />
    </main>
  );
}
