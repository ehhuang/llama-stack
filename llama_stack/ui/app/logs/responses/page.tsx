"use client";

import { useEffect, useState } from "react";
import LlamaStackClient from "llama-stack-client";
import { OpenAIResponse } from "@/lib/types";
import { ResponsesTable } from "@/components/responses/responses-table";

export default function ResponsesPage() {
  const [responses, setResponses] = useState<OpenAIResponse[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const client = new LlamaStackClient({
      baseURL: process.env.NEXT_PUBLIC_LLAMA_STACK_BASE_URL,
    });

    const fetchResponses = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await client.responses.list();
        let data: unknown[] = [];

        if (Array.isArray(response)) {
          data = response;
        } else if (
          response &&
          typeof response === "object" &&
          "data" in response
        ) {
          const responseData = (response as { data: unknown[] }).data;
          if (Array.isArray(responseData)) {
            data = responseData;
          }
        }

        // Convert the data to match our OpenAIResponse interface
        const convertedResponses: OpenAIResponse[] = data.map(
          (item: unknown) => {
            const responseItem = item as Record<string, unknown>;
            return {
              id: String(responseItem.id || ""),
              created_at: Number(responseItem.created_at || 0),
              model: String(responseItem.model || ""),
              object: "response" as const,
              status: String(responseItem.status || ""),
              output: (responseItem.output as OpenAIResponse["output"]) || [],
              input: (responseItem.input as OpenAIResponse["input"]) || [],
              error: responseItem.error as OpenAIResponse["error"],
              parallel_tool_calls: Boolean(responseItem.parallel_tool_calls),
              previous_response_id: responseItem.previous_response_id as string,
              temperature: responseItem.temperature as number,
              top_p: responseItem.top_p as number,
              truncation: responseItem.truncation as string,
              user: responseItem.user as string,
            };
          },
        );

        setResponses(convertedResponses);
      } catch (err) {
        console.error("Error fetching responses:", err);
        setError(
          err instanceof Error ? err : new Error("Failed to fetch responses"),
        );
        setResponses([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchResponses();
  }, []);

  return (
    <ResponsesTable data={responses} isLoading={isLoading} error={error} />
  );
}
