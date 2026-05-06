// src/store/travelStore.ts
// ============================================================
//  Zustand global store — travel plan + UI state
//  Import useTravelStore in any component that needs this data.
// ============================================================

import { create } from "zustand";
import type { TravelPlanResponse, TravelQueryRequest, FileAnalysisResponse } from "@/lib/api/types";

interface TravelStore {
  // Current query the user submitted
  currentQuery: TravelQueryRequest | null;
  setCurrentQuery: (q: TravelQueryRequest) => void;

  // Generated plan
  travelPlan: TravelPlanResponse | null;
  setTravelPlan: (plan: TravelPlanResponse) => void;
  clearPlan: () => void;

  // Uploaded file analysis result
  fileAnalysis: FileAnalysisResponse | null;
  setFileAnalysis: (result: FileAnalysisResponse) => void;

  // UI state
  activeTab: "plan" | "chat" | "search" | "upload";
  setActiveTab: (tab: "plan" | "chat" | "search" | "upload") => void;
}

export const useTravelStore = create<TravelStore>((set) => ({
  currentQuery:  null,
  travelPlan:    null,
  fileAnalysis:  null,
  activeTab:     "plan",

  setCurrentQuery: (q)      => set({ currentQuery: q }),
  setTravelPlan:   (plan)   => set({ travelPlan: plan }),
  clearPlan:       ()       => set({ travelPlan: null, currentQuery: null }),
  setFileAnalysis: (result) => set({ fileAnalysis: result }),
  setActiveTab:    (tab)    => set({ activeTab: tab }),
}));
