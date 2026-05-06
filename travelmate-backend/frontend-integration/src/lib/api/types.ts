// src/lib/api/types.ts
// ============================================================
//  TypeScript interfaces — mirror backend Pydantic schemas
//  Keep these in sync with app/schemas/travel.py
// ============================================================

// ── Enums ────────────────────────────────────────────────────
export type TripType     = "leisure" | "adventure" | "business" | "family" | "romantic";
export type BudgetLevel  = "budget" | "moderate" | "luxury";
export type LlmProvider  = "groq" | "gemini";

// ── Travel Query ─────────────────────────────────────────────
export interface TravelQueryRequest {
  origin: string;
  destination: string;
  departure_date: string;       // YYYY-MM-DD
  return_date: string;          // YYYY-MM-DD
  travelers: number;
  budget_usd: number;
  budget_level: BudgetLevel;
  trip_type: TripType;
  extra_notes?: string;
}

// ── Chat ─────────────────────────────────────────────────────
export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface ChatRequest {
  message: string;
  history?: ChatMessage[];
  travel_context?: TravelQueryRequest;
  session_id?: string;
}

export interface ChatResponse {
  reply: string;
  sources: string[];
  llm_used: LlmProvider;
  session_id: string;
}

// ── Search Results ───────────────────────────────────────────
export interface FlightResult {
  airline: string;
  route: string;
  estimated_price_usd: number;
  duration?: string;
  notes?: string;
}

export interface HotelResult {
  name: string;
  location: string;
  price_per_night_usd: number;
  rating?: number;
  amenities: string[];
  notes?: string;
}

export interface ActivityResult {
  name: string;
  category: string;
  estimated_cost_usd: number;
  duration?: string;
  description?: string;
}

// ── Full Travel Plan ─────────────────────────────────────────
export interface DayPlan {
  day: number;
  date: string;
  morning: string;
  afternoon: string;
  evening: string;
  estimated_daily_cost_usd: number;
}

export interface TravelPlanResponse {
  destination: string;
  origin: string;
  duration_days: number;
  travelers: number;
  total_estimated_cost_usd: number;
  budget_usd: number;
  budget_level: BudgetLevel;
  trip_type: TripType;
  summary: string;
  highlights: string[];
  flights: FlightResult[];
  hotels: HotelResult[];
  activities: ActivityResult[];
  day_by_day: DayPlan[];
  tips: string[];
  llm_used: LlmProvider;
  search_sources: string[];
}

// ── File Analysis ─────────────────────────────────────────────
export interface FileAnalysisResponse {
  filename: string;
  file_type: string;
  extracted_text: string;
  travel_insights: string;
  detected_destinations: string[];
  detected_dates: string[];
  llm_used: LlmProvider;
}

// ── Health Check ─────────────────────────────────────────────
export interface HealthResponse {
  status: "ok" | "degraded";
  version: string;
  services: Record<string, string>;
}
