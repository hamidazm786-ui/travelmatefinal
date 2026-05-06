// src/hooks/useTravelMate.ts
// ============================================================
//  React Query hooks — use these in components for data fetching
//  Handles loading, error, and caching automatically.
// ============================================================

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, useCallback } from "react";
import {
  generateTravelPlan,
  sendChatMessage,
  clearChatSession,
  analyzeFile,
  checkHealth,
  searchDestination,
} from "@/lib/api/travelmate";
import type {
  TravelQueryRequest,
  TravelPlanResponse,
  ChatMessage,
  ChatResponse,
  FileAnalysisResponse,
} from "@/lib/api/types";

// ── Health check query ───────────────────────────────────────
export const useHealthCheck = () => {
  return useQuery({
    queryKey: ["health"],
    queryFn: checkHealth,
    refetchInterval: 30_000, // check every 30s
    retry: 2,
  });
};

// ── Travel Plan mutation ─────────────────────────────────────
export const useTravelPlan = () => {
  return useMutation<TravelPlanResponse, Error, TravelQueryRequest>({
    mutationFn: generateTravelPlan,
    onSuccess: (data) => {
      console.log(`[TravelMate] Plan generated via ${data.llm_used}`);
    },
    onError: (error) => {
      console.error("[TravelMate] Plan generation failed:", error.message);
    },
  });
};

// ── Chat hook with session management ────────────────────────
export const useChat = () => {
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [history, setHistory] = useState<ChatMessage[]>([]);

  const sendMessage = useMutation<ChatResponse, Error, {
    message: string;
    travelContext?: TravelQueryRequest;
  }>({
    mutationFn: async ({ message, travelContext }) => {
      const response = await sendChatMessage({
        message,
        history,
        travel_context: travelContext,
        session_id: sessionId,
      });
      return response;
    },
    onSuccess: (data, variables) => {
      // Persist session ID from first response
      if (!sessionId && data.session_id) {
        setSessionId(data.session_id);
      }
      // Update local history
      setHistory((prev) => [
        ...prev,
        { role: "user",      content: variables.message },
        { role: "assistant", content: data.reply },
      ]);
    },
  });

  const clearHistory = useCallback(async () => {
    if (sessionId) {
      await clearChatSession(sessionId);
    }
    setSessionId(undefined);
    setHistory([]);
  }, [sessionId]);

  return {
    sendMessage,
    history,
    sessionId,
    clearHistory,
    isLoading: sendMessage.isPending,
    error: sendMessage.error,
  };
};

// ── File analysis mutation ────────────────────────────────────
export const useFileAnalysis = () => {
  return useMutation<FileAnalysisResponse, Error, File>({
    mutationFn: analyzeFile,
  });
};

// ── Destination search query ──────────────────────────────────
export const useDestinationSearch = (destination: string) => {
  return useQuery({
    queryKey: ["destination", destination],
    queryFn: () => searchDestination(destination),
    enabled: destination.length > 2,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};
