import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  ArrowUp,
  Copy,
  ExternalLink,
  Globe2,
  MapPin,
  MessageCircle,
  Paperclip,
  Plus,
  Search,
  Share2,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useChatStore } from "@/lib/chatStore";
import {
  apiCreateSession,
  apiDeleteSession,
  apiGetSession,
  apiListSessions,
  apiSendMessage,
  demoReply,
  DEMO_SUGGESTIONS,
  pingBackend,
  type ChatMessage,
  type TravelContext,
} from "@/lib/chatApi";
import { useTravelmate } from "@/lib/store";

const uid = () => Math.random().toString(36).slice(2, 10);

function ModelBadge({ llm }: { llm?: string }) {
  if (!llm) return null;
  const isGroq = /groq|llama/i.test(llm);
  const isGemini = /gemini/i.test(llm);
  const color = isGroq
    ? "text-sky-300 border-sky-400/30 bg-sky-400/5"
    : isGemini
      ? "text-violet-300 border-violet-400/30 bg-violet-400/5"
      : "text-muted-foreground border-gold/20";
  const label = isGroq ? "via Groq" : isGemini ? "via Gemini" : "via " + llm;
  return (
    <span className={cn("font-mono text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded border", color)}>
      {label}
    </span>
  );
}

function TypingDots() {
  return (
    <div className="flex items-center gap-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-gold animate-bounce"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </div>
  );
}

function MessageBubble({ m }: { m: ChatMessage }) {
  const isUser = m.role === "user";
  const time = new Date(m.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  if (isUser) {
    return (
      <div className="flex items-start justify-end gap-3 group">
        <div className="max-w-[70%] flex flex-col items-end">
          <div
            className="px-4 py-2.5 text-sm leading-relaxed text-foreground"
            style={{
              background: "hsl(38 42% 59% / 0.12)",
              border: "1px solid hsl(38 42% 59% / 0.25)",
              borderRadius: "18px 18px 4px 18px",
            }}
          >
            {m.content}
          </div>
          <span className="font-mono text-[10px] text-muted-foreground mt-1">{time}</span>
        </div>
        <div className="h-8 w-8 rounded-full bg-gradient-to-br from-gold to-gold-deep flex items-center justify-center text-[11px] font-medium text-ink shrink-0">
          AT
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3 group">
      <div className="h-8 w-8 rounded-full bg-ink-soft border border-gold/30 flex items-center justify-center shrink-0">
        <Globe2 className="h-4 w-4 text-gold" />
      </div>
      <div className="max-w-[70%] flex flex-col items-start">
        <div
          className="px-4 py-3 bg-card border border-white/[0.06] text-sm leading-relaxed"
          style={{ borderRadius: "4px 18px 18px 18px" }}
        >
          <div className="prose prose-sm prose-invert max-w-none prose-headings:text-gold prose-strong:text-gold-bright prose-a:text-gold prose-code:text-gold prose-li:my-0.5">
            <ReactMarkdown>{m.content}</ReactMarkdown>
          </div>
          {m.sources && m.sources.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-white/5">
              {m.sources.map((s, i) => (
                <a
                  key={i}
                  href={s.startsWith("http") ? s : `https://${s}`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-ink border border-gold/25 text-[10px] font-mono text-gold hover:border-gold/60 transition-colors"
                >
                  <ExternalLink className="h-2.5 w-2.5" /> {s.replace(/^https?:\/\//, "")}
                </a>
              ))}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2 mt-1">
          <ModelBadge llm={m.llm_used} />
          <span className="font-mono text-[10px] text-muted-foreground">{time}</span>
          <button
            onClick={() => {
              navigator.clipboard.writeText(m.content);
              toast.success("Copied to clipboard");
            }}
            className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-ink-soft"
            aria-label="Copy"
          >
            <Copy className="h-3 w-3 text-muted-foreground" />
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Chat() {
  const {
    sessions,
    activeId,
    messages,
    loading,
    demoMode,
    travelContext,
    contextLabel,
    setActive,
    newLocalSession,
    appendMessage,
    setMessages,
    removeSession,
    renameSession,
    setLoading,
    setDemoMode,
    setSessions,
    setContext,
  } = useChatStore();

  const history = useTravelmate((s) => s.history);

  const [input, setInput] = useState("");
  const [search, setSearch] = useState("");
  const [contextOpen, setContextOpen] = useState(false);
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [editingTitle, setEditingTitle] = useState(false);

  const inputRef = useRef<HTMLTextAreaElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // Detect backend on mount
  useEffect(() => {
    (async () => {
      const ok = await pingBackend();
      setDemoMode(!ok);
      if (ok) {
        try {
          const list = await apiListSessions();
          if (Array.isArray(list) && list.length) setSessions(list);
        } catch {
          /* ignore */
        }
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-scroll
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [activeId, loading, messages]);

  // Auto-resize textarea
  useEffect(() => {
    const ta = inputRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 6 * 24) + "px";
  }, [input]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
      if (e.ctrlKey && e.key === "n") {
        e.preventDefault();
        newLocalSession();
      }
      if (e.key === "Escape") setContextOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [newLocalSession]);

  const activeSession = sessions.find((s) => s.id === activeId);
  const activeMessages = activeId ? messages[activeId] ?? [] : [];

  const filteredSessions = useMemo(
    () =>
      sessions.filter((s) =>
        s.title.toLowerCase().includes(search.toLowerCase()),
      ),
    [sessions, search],
  );

  async function selectSession(id: string) {
    setActive(id);
    if (!demoMode && !messages[id]) {
      try {
        const s = await apiGetSession(id);
        setMessages(id, s.messages ?? []);
      } catch {
        /* ignore */
      }
    }
  }

  async function handleNew() {
    if (demoMode) {
      newLocalSession();
      return;
    }
    try {
      const s = await apiCreateSession(travelContext);
      const local = newLocalSession();
      // swap id
      renameSession(local, "New conversation");
      setActive(s.id);
      setMessages(s.id, []);
      setSessions([{ id: s.id, title: "New conversation", created_at: Date.now(), message_count: 0 }, ...sessions]);
    } catch {
      newLocalSession();
    }
  }

  async function handleDelete(id: string) {
    if (!demoMode) {
      try {
        await apiDeleteSession(id);
      } catch {
        /* ignore */
      }
    }
    removeSession(id);
    toast.success("Conversation deleted");
  }

  async function handleSend(text?: string) {
    const message = (text ?? input).trim();
    if (!message || loading) return;
    let sid = activeId;
    if (!sid) sid = newLocalSession();

    const userMsg: ChatMessage = {
      id: uid(),
      role: "user",
      content: message,
      timestamp: Date.now(),
    };
    appendMessage(sid, userMsg);
    setInput("");
    setAttachedFile(null);
    setLoading(true);

    try {
      if (demoMode) {
        await new Promise((r) => setTimeout(r, 1500 + Math.random() * 1000));
        const reply = demoReply(message);
        appendMessage(sid, {
          id: uid(),
          role: "assistant",
          content: reply.reply,
          timestamp: Date.now(),
          llm_used: reply.llm,
          sources: reply.sources,
        });
      } else {
        const res = await apiSendMessage(sid, message, travelContext);
        appendMessage(sid, {
          id: uid(),
          role: "assistant",
          content: res.reply,
          timestamp: Date.now(),
          llm_used: res.llm_used,
          sources: res.sources,
        });
      }
    } catch {
      toast.error("Failed to send. Switching to demo mode.");
      setDemoMode(true);
      const reply = demoReply(message);
      appendMessage(sid, {
        id: uid(),
        role: "assistant",
        content: reply.reply,
        timestamp: Date.now(),
        llm_used: reply.llm,
        sources: reply.sources,
      });
    } finally {
      setLoading(false);
    }
  }

  const lastLlm = [...activeMessages].reverse().find((m) => m.llm_used)?.llm_used;

  return (
    <div className="flex h-[calc(100vh-6.5rem)] overflow-hidden">
      {/* LEFT SIDEBAR */}
      <aside className="hidden md:flex w-[280px] flex-col border-r border-gold/15 bg-[hsl(240_22%_6%)]">
        <div className="p-4 border-b border-gold/15">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-display text-xl">Conversations</h2>
            <button
              onClick={handleNew}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-gradient-to-br from-gold to-gold-deep text-ink text-xs font-medium hover:shadow-[0_0_12px_hsl(var(--gold)/0.4)] transition-shadow"
            >
              <Plus className="h-3 w-3" /> New
            </button>
          </div>
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search conversations…"
              className="ti pl-8 text-xs"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {filteredSessions.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center gap-2 text-muted-foreground p-4">
              <MessageCircle className="h-8 w-8 text-gold/40" />
              <p className="text-xs">No conversations yet</p>
            </div>
          )}
          {filteredSessions.map((s) => {
            const active = s.id === activeId;
            return (
              <div
                key={s.id}
                onClick={() => selectSession(s.id)}
                className={cn(
                  "group relative px-3 py-2 rounded-md cursor-pointer transition-all border-l-2",
                  active
                    ? "bg-gold/10 border-l-gold"
                    : "border-l-transparent hover:bg-ink-soft",
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <p className={cn("text-xs truncate", active ? "text-gold" : "text-foreground/90")}>
                      {s.title}
                    </p>
                    <p className="font-mono text-[9px] text-muted-foreground mt-0.5">
                      {new Date(s.created_at).toLocaleDateString()} · {s.message_count} msg
                    </p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(s.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-destructive/20 transition-opacity"
                    aria-label="Delete"
                  >
                    <Trash2 className="h-3 w-3 text-destructive/80" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        <div className="p-3 border-t border-gold/15 flex items-center gap-2">
          <div className="h-7 w-7 rounded-full bg-gradient-to-br from-gold to-gold-deep flex items-center justify-center text-[10px] font-medium text-ink">
            AT
          </div>
          <div className="min-w-0">
            <p className="text-xs truncate">Anonymous Traveller</p>
            <p className="font-mono text-[9px] text-muted-foreground">Powered by Groq + Gemini</p>
          </div>
        </div>
      </aside>

      {/* MAIN CHAT */}
      <section className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-14 px-4 md:px-6 border-b border-gold/15 flex items-center justify-between gap-3 bg-ink/60 backdrop-blur">
          <div className="min-w-0 flex items-center gap-3">
            {editingTitle && activeSession ? (
              <input
                autoFocus
                defaultValue={activeSession.title}
                onBlur={(e) => {
                  renameSession(activeSession.id, e.target.value || activeSession.title);
                  setEditingTitle(false);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") (e.target as HTMLInputElement).blur();
                }}
                className="ti text-sm max-w-md"
              />
            ) : (
              <h1
                onClick={() => activeSession && setEditingTitle(true)}
                className="font-display text-lg truncate cursor-text"
              >
                {activeSession?.title ?? "New conversation"}
              </h1>
            )}
            {lastLlm && <ModelBadge llm={lastLlm} />}
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => activeId && setMessages(activeId, [])}
              className="p-2 rounded-md hover:bg-ink-soft text-foreground/70"
              aria-label="Clear"
            >
              <Trash2 className="h-4 w-4" />
            </button>
            <button
              onClick={() => {
                navigator.clipboard.writeText(window.location.href);
                toast.success("Link copied");
              }}
              className="p-2 rounded-md hover:bg-ink-soft text-foreground/70"
              aria-label="Share"
            >
              <Share2 className="h-4 w-4" />
            </button>
            <button
              onClick={() => setContextOpen((o) => !o)}
              className={cn(
                "p-2 rounded-md transition-colors",
                contextOpen ? "bg-gold/10 text-gold" : "hover:bg-ink-soft text-foreground/70",
              )}
              aria-label="Trip context"
            >
              <MapPin className="h-4 w-4" />
            </button>
          </div>
        </header>

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 md:px-8 py-6">
          {activeMessages.length === 0 && !loading ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-2xl mx-auto">
              <div
                className="h-20 w-20 rounded-full bg-gold/10 border border-gold/30 flex items-center justify-center mb-6"
                style={{ animation: "float-slow 4s ease-in-out infinite" }}
              >
                <Globe2 className="h-10 w-10 text-gold" />
              </div>
              <h2 className="font-display text-4xl mb-3">Ask me anything about travel</h2>
              <p className="text-muted-foreground max-w-md mb-8">
                I can help plan trips, suggest destinations, answer visa questions, compare hotels, and much more.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full">
                {DEMO_SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => handleSend(s)}
                    className="text-left p-3 rounded-lg bg-card border border-gold/15 hover:border-gold/50 transition-colors text-sm"
                  >
                    <Sparkles className="h-3.5 w-3.5 text-gold mb-1.5" />
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-6">
              {activeMessages.map((m) => (
                <MessageBubble key={m.id} m={m} />
              ))}
              {loading && (
                <div className="flex items-start gap-3">
                  <div className="h-8 w-8 rounded-full bg-ink-soft border border-gold/30 flex items-center justify-center">
                    <Globe2 className="h-4 w-4 text-gold" />
                  </div>
                  <div
                    className="px-4 py-3 bg-card border border-white/[0.06] flex items-center gap-3"
                    style={{ borderRadius: "4px 18px 18px 18px" }}
                  >
                    <TypingDots />
                    <span className="text-xs text-muted-foreground">TravelMate is thinking…</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-gold/15 bg-ink/80 backdrop-blur px-4 md:px-8 py-4">
          <div className="max-w-3xl mx-auto">
            {(attachedFile || contextLabel) && (
              <div className="flex flex-wrap gap-2 mb-2">
                {attachedFile && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-card border border-gold/30 text-xs">
                    <Paperclip className="h-3 w-3 text-gold" />
                    {attachedFile.name}
                    <button onClick={() => setAttachedFile(null)} aria-label="Remove file">
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                )}
                {contextLabel && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-gold/10 border border-gold/40 text-xs text-gold">
                    <MapPin className="h-3 w-3" />
                    Trip: {contextLabel}
                    <button onClick={() => setContext(null, null)} aria-label="Detach">
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                )}
              </div>
            )}
            <div className="relative flex items-end gap-2 p-2 rounded-2xl bg-[hsl(240_22%_6%)] border border-gold/20 focus-within:border-gold/50 focus-within:shadow-[0_0_0_3px_hsl(var(--gold)/0.1)] transition-all">
              <input
                ref={fileRef}
                type="file"
                accept=".pdf,.txt,.docx"
                className="hidden"
                onChange={(e) => setAttachedFile(e.target.files?.[0] ?? null)}
              />
              <button
                onClick={() => fileRef.current?.click()}
                className="p-2 rounded-md text-foreground/60 hover:text-gold hover:bg-ink-soft"
                aria-label="Attach file"
              >
                <Paperclip className="h-4 w-4" />
              </button>
              <button
                onClick={() => setContextOpen(true)}
                className="p-2 rounded-md text-foreground/60 hover:text-gold hover:bg-ink-soft"
                aria-label="Trip context"
              >
                <MapPin className="h-4 w-4" />
              </button>
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder="Ask TravelMate about destinations, flights, hotels, visas…"
                rows={1}
                className="flex-1 resize-none bg-transparent outline-none text-sm py-2 placeholder:text-muted-foreground/60 max-h-36"
              />
              {input.length > 500 && (
                <span className="font-mono text-[10px] text-muted-foreground self-center">
                  {input.length}
                </span>
              )}
              <button
                onClick={() => handleSend()}
                disabled={!input.trim() || loading}
                className="h-9 w-9 rounded-full bg-gradient-to-br from-gold to-gold-deep text-ink flex items-center justify-center disabled:opacity-30 disabled:cursor-not-allowed enabled:hover:shadow-[0_0_18px_hsl(var(--gold)/0.5)] transition-shadow"
                aria-label="Send"
              >
                <ArrowUp className="h-4 w-4" />
              </button>
            </div>
            <p className="font-mono text-[10px] text-muted-foreground text-center mt-2">
              ↵ Enter to send · Shift+Enter for new line · Groq + Gemini AI · Not financial advice
            </p>
          </div>
        </div>
      </section>

      {/* RIGHT CONTEXT PANEL */}
      {contextOpen && (
        <aside className="hidden lg:flex w-[320px] flex-col border-l border-gold/15 bg-[hsl(240_22%_6%)]">
          <div className="p-4 border-b border-gold/15 flex items-center justify-between">
            <h3 className="font-display text-lg">Trip Context</h3>
            <button onClick={() => setContextOpen(false)} className="p-1 rounded hover:bg-ink-soft">
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {contextLabel && travelContext ? (
              <div className="card-luxury p-3">
                <p className="text-xs text-muted-foreground mb-1">Currently attached</p>
                <p className="font-display text-lg text-gold">{travelContext.destination}</p>
                <p className="text-xs">
                  {travelContext.start_date} → {travelContext.end_date}
                </p>
                <p className="text-xs text-muted-foreground">
                  ${travelContext.budget} · {travelContext.travelers} travellers
                </p>
                <button
                  onClick={() => setContext(null, null)}
                  className="mt-2 text-xs text-destructive hover:underline"
                >
                  Detach
                </button>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">No trip attached.</p>
            )}

            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground mb-2 font-mono">
                Attach a recent trip
              </p>
              <div className="space-y-2">
                {history.slice(0, 5).map((t) => (
                  <button
                    key={t.id}
                    onClick={() => {
                      setContext(
                        {
                          destination: t.destination,
                          start_date: t.start_date,
                          end_date: t.end_date,
                          budget: t.total_cost,
                          travelers: 2,
                        },
                        `${t.destination} ${t.start_date}`,
                      );
                      toast.success(`Attached: ${t.destination}`);
                    }}
                    className="w-full text-left p-3 rounded-md bg-card border border-gold/15 hover:border-gold/50 transition-colors"
                  >
                    <p className="text-sm">{t.destination}</p>
                    <p className="font-mono text-[10px] text-muted-foreground">
                      {t.start_date} → {t.end_date}
                    </p>
                  </button>
                ))}
              </div>
            </div>

            <div className="text-xs text-muted-foreground border-t border-gold/10 pt-3">
              <p className="font-medium text-foreground/80 mb-1">What this does</p>
              Attaching a trip lets TravelMate answer questions specifically about your planned journey.
            </div>
          </div>
        </aside>
      )}
    </div>
  );
}
