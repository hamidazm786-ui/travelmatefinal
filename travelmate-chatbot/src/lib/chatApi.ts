// Travelmate chat API client with graceful demo fallback
export const CHAT_API_BASE =
  (import.meta.env.VITE_CHAT_API_BASE as string | undefined) || "http://localhost:8000/api/v1";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  llm_used?: string;
  sources?: string[];
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: number;
  message_count: number;
  messages?: ChatMessage[];
}

export interface TravelContext {
  destination?: string;
  start_date?: string;
  end_date?: string;
  budget?: number;
  travelers?: number;
}

const TIMEOUT_MS = 2500;

async function withTimeout<T>(p: Promise<T>, ms = TIMEOUT_MS): Promise<T> {
  return await Promise.race([
    p,
    new Promise<T>((_, rej) => setTimeout(() => rej(new Error("timeout")), ms)),
  ]);
}

export async function pingBackend(): Promise<boolean> {
  try {
    await withTimeout(fetch(`${CHAT_API_BASE}/chat/sessions`, { method: "GET" }), 1500);
    return true;
  } catch {
    return false;
  }
}

export async function apiCreateSession(travel_context?: TravelContext | null) {
  const res = await withTimeout(
    fetch(`${CHAT_API_BASE}/chat/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ travel_context: travel_context ?? null }),
    }),
  );
  return (await res.json()) as { id: string };
}

export async function apiSendMessage(
  sessionId: string,
  message: string,
  travel_context?: TravelContext | null,
) {
  const res = await withTimeout(
    fetch(`${CHAT_API_BASE}/chat/sessions/${sessionId}/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        history: [],
        travel_context: travel_context ?? null,
        session_id: sessionId,
      }),
    }),
    20000,
  );
  return (await res.json()) as {
    reply: string;
    sources?: string[];
    llm_used?: string;
    session_id: string;
  };
}

export async function apiListSessions() {
  const res = await withTimeout(fetch(`${CHAT_API_BASE}/chat/sessions`));
  return (await res.json()) as ChatSession[];
}

export async function apiGetSession(id: string) {
  const res = await withTimeout(fetch(`${CHAT_API_BASE}/chat/sessions/${id}`));
  return (await res.json()) as ChatSession;
}

export async function apiDeleteSession(id: string) {
  await withTimeout(
    fetch(`${CHAT_API_BASE}/chat/sessions/${id}`, { method: "DELETE" }),
  );
}

// ---------------- DEMO MODE ----------------
const DEMO_REPLIES: Array<{ match: RegExp; reply: string; sources: string[]; llm: string }> = [
  {
    match: /tokyo/i,
    reply:
      "**Tokyo in 7 days under $2000** is doable if you stay outside Shinjuku and use a JR pass.\n\n- **Stay:** Granbell Shibuya (~$180/night) or capsule hotels in Asakusa for $40\n- **Eat:** Convenience stores + neighbourhood ramen — averages $25/day\n- **Don't miss:** TeamLab Planets, Senso-ji at sunrise, a day trip to Kamakura\n\nWant me to draft a full day-by-day plan?",
    sources: ["japan-guide.com", "tripadvisor.com"],
    llm: "groq/llama3-70b",
  },
  {
    match: /bali|surf/i,
    reply:
      "Best time to surf Bali is **April – October** (dry season).\n\n1. **Beginners:** Kuta, Canggu (Old Man's, Batu Bolong)\n2. **Intermediate:** Uluwatu, Padang Padang\n3. **Advanced:** Desert Point (Lombok), Keramas\n\nSwell is most consistent in **June–August** — book ahead, accommodation triples in price.",
    sources: ["surfline.com", "magicseaweed.com"],
    llm: "google/gemini-flash",
  },
  {
    match: /visa|pakistan|turkey/i,
    reply:
      "**Pakistani passport → Turkey:** e-Visa available online.\n\n- Cost: **$60**, processed in ~24h\n- Validity: 180 days, single entry, 30 days stay\n- Apply at: evisa.gov.tr\n- Required: passport (6mo validity), return ticket, hotel booking\n\nNo embassy visit needed for tourism.",
    sources: ["evisa.gov.tr", "iatatravelcentre.com"],
    llm: "google/gemini-flash",
  },
  {
    match: /business class|economy|long haul/i,
    reply:
      "**Business vs Economy on long-haul (>8h):**\n\n| | Economy | Business |\n|---|---|---|\n| Price | $700–1,200 | $3,000–6,500 |\n| Sleep | Hard | Lie-flat |\n| Lounge | No | Yes |\n| Bags | 1×23kg | 2×32kg |\n\nIf you arrive and **work the next day**, business pays for itself. For leisure with a buffer day, economy + a hotel night is usually smarter.",
    sources: ["seatguru.com", "thepointsguy.com"],
    llm: "groq/llama3-70b",
  },
];

const DEFAULT_DEMO = {
  reply:
    "I'd love to help with that! In **demo mode** I'm returning simulated replies — connect the FastAPI backend at `localhost:8000` to get live answers from Groq + Gemini grounded with real travel sources.",
  sources: ["lovable.dev"],
  llm: "demo/simulated",
};

export function demoReply(message: string) {
  const hit = DEMO_REPLIES.find((r) => r.match.test(message));
  return hit ?? DEFAULT_DEMO;
}

export const DEMO_SUGGESTIONS = [
  "Plan a 7-day trip to Tokyo under $2000",
  "Best time to visit Bali for surfing?",
  "Compare business class vs economy for long haul",
  "Visa requirements for Pakistan to Turkey",
];
