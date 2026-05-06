// src/lib/api/travelmate.ts
// ============================================================
//  TravelMate API functions — call these from React components
//  All functions are typed end-to-end with backend schemas.
// ============================================================

import { apiClient } from "./client";
import type {
  TravelQueryRequest,
  TravelPlanResponse,
  ChatRequest,
  ChatResponse,
  FileAnalysisResponse,
  HealthResponse,
} from "./types";

// ── Health ───────────────────────────────────────────────────

export const checkHealth = async (): Promise<HealthResponse> => {
  const { data } = await apiClient.get<HealthResponse>("/api/v1/health/");
  return data;
};

// ── Travel Plan ───────────────────────────────────────────────

/**
 * Generate a complete AI travel plan.
 * Calls POST /api/v1/travel/plan
 * Backend: searches web → generates LLM itinerary → returns structured plan
 */
export const generateTravelPlan = async (
  query: TravelQueryRequest
): Promise<TravelPlanResponse> => {
  const { data } = await apiClient.post<TravelPlanResponse>("/api/v1/travel/plan", query);
  return data;
};

// ── Chat ──────────────────────────────────────────────────────

/**
 * Send a chat message to TravelMate AI.
 * Pass session_id to maintain conversation history.
 */
export const sendChatMessage = async (request: ChatRequest): Promise<ChatResponse> => {
  const { data } = await apiClient.post<ChatResponse>("/api/v1/chat/message", request);
  return data;
};

/**
 * Clear conversation history for a session.
 */
export const clearChatSession = async (sessionId: string): Promise<void> => {
  await apiClient.delete(`/api/v1/chat/session/${sessionId}`);
};

// ── Search ────────────────────────────────────────────────────

export const searchDestination = async (destination: string) => {
  const { data } = await apiClient.get("/api/v1/search/destination", {
    params: { destination },
  });
  return data;
};

export const searchFlights = async (
  origin: string,
  destination: string,
  date: string
) => {
  const { data } = await apiClient.get("/api/v1/search/flights", {
    params: { origin, destination, date },
  });
  return data;
};

export const searchHotels = async (
  destination: string,
  checkIn: string,
  checkOut: string,
  budgetLevel: string = "moderate"
) => {
  const { data } = await apiClient.get("/api/v1/search/hotels", {
    params: { destination, check_in: checkIn, check_out: checkOut, budget_level: budgetLevel },
  });
  return data;
};

export const searchActivities = async (destination: string, tripType: string = "leisure") => {
  const { data } = await apiClient.get("/api/v1/search/activities", {
    params: { destination, trip_type: tripType },
  });
  return data;
};

// ── File Upload ───────────────────────────────────────────────

/**
 * Upload a travel document (PDF, DOCX, TXT, image) for AI analysis.
 */
export const analyzeFile = async (file: File): Promise<FileAnalysisResponse> => {
  const formData = new FormData();
  formData.append("file", file);

  const { data } = await apiClient.post<FileAnalysisResponse>(
    "/api/v1/files/analyze",
    formData,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return data;
};
