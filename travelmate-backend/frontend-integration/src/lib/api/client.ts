// src/lib/api/client.ts
// ============================================================
//  Axios HTTP client — configured to talk to FastAPI backend
//  Import this instead of creating new axios instances.
// ============================================================

import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 120_000, // 2 min — LLM calls can be slow
});

// ── Request interceptor — add auth token if present ─────────
apiClient.interceptors.request.use((config) => {
  // If you add auth later, inject token here:
  // const token = localStorage.getItem("token");
  // if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ── Response interceptor — normalize errors ─────────────────
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.message ||
      "An unexpected error occurred";
    return Promise.reject(new Error(message));
  }
);
