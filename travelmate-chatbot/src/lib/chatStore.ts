import { create } from "zustand";
import type { ChatMessage, ChatSession, TravelContext } from "./chatApi";

const uid = () => Math.random().toString(36).slice(2, 10);

const seedSessions = (): ChatSession[] => [
  {
    id: "demo-tokyo",
    title: "Tokyo trip planning, 7 days under $2k",
    created_at: Date.now() - 1000 * 60 * 60 * 24 * 2,
    message_count: 4,
    messages: [
      { id: uid(), role: "user", content: "Plan a 7-day trip to Tokyo under $2000", timestamp: Date.now() - 86400000 },
      {
        id: uid(),
        role: "assistant",
        content:
          "**Tokyo in 7 days under $2000** is doable. Stay in Asakusa, use a JR pass, and eat at neighbourhood ramen shops. Want a day-by-day plan?",
        timestamp: Date.now() - 86400000 + 4000,
        llm_used: "groq/llama3-70b",
        sources: ["japan-guide.com"],
      },
    ],
  },
  {
    id: "demo-visa",
    title: "Visa requirements Pakistan to Turkey",
    created_at: Date.now() - 1000 * 60 * 60 * 6,
    message_count: 2,
  },
];

interface ChatStoreState {
  demoMode: boolean;
  setDemoMode: (b: boolean) => void;

  sessions: ChatSession[];
  activeId: string | null;
  messages: Record<string, ChatMessage[]>; // by sessionId
  loading: boolean;
  travelContext: TravelContext | null;
  contextLabel: string | null;

  setSessions: (s: ChatSession[]) => void;
  setActive: (id: string | null) => void;
  newLocalSession: () => string;
  appendMessage: (sid: string, m: ChatMessage) => void;
  setMessages: (sid: string, list: ChatMessage[]) => void;
  removeSession: (id: string) => void;
  renameSession: (id: string, title: string) => void;
  setLoading: (b: boolean) => void;
  setContext: (ctx: TravelContext | null, label: string | null) => void;
}

export const useChatStore = create<ChatStoreState>((set, get) => ({
  demoMode: true,
  setDemoMode: (b) => set({ demoMode: b }),

  sessions: seedSessions(),
  activeId: "demo-tokyo",
  messages: { "demo-tokyo": seedSessions()[0].messages! },
  loading: false,
  travelContext: null,
  contextLabel: null,

  setSessions: (sessions) => set({ sessions }),
  setActive: (activeId) => set({ activeId }),
  newLocalSession: () => {
    const id = "local-" + uid();
    const s: ChatSession = { id, title: "New conversation", created_at: Date.now(), message_count: 0 };
    set((st) => ({ sessions: [s, ...st.sessions], activeId: id, messages: { ...st.messages, [id]: [] } }));
    return id;
  },
  appendMessage: (sid, m) =>
    set((st) => {
      const list = [...(st.messages[sid] ?? []), m];
      const sessions = st.sessions.map((s) =>
        s.id === sid
          ? {
              ...s,
              message_count: list.length,
              title:
                s.title === "New conversation" && m.role === "user"
                  ? m.content.slice(0, 50)
                  : s.title,
            }
          : s,
      );
      return { messages: { ...st.messages, [sid]: list }, sessions };
    }),
  setMessages: (sid, list) =>
    set((st) => ({ messages: { ...st.messages, [sid]: list } })),
  removeSession: (id) =>
    set((st) => {
      const sessions = st.sessions.filter((s) => s.id !== id);
      const { [id]: _, ...rest } = st.messages;
      return {
        sessions,
        messages: rest,
        activeId: st.activeId === id ? sessions[0]?.id ?? null : st.activeId,
      };
    }),
  renameSession: (id, title) =>
    set((st) => ({ sessions: st.sessions.map((s) => (s.id === id ? { ...s, title } : s)) })),
  setLoading: (loading) => set({ loading }),
  setContext: (travelContext, contextLabel) => set({ travelContext, contextLabel }),
}));
