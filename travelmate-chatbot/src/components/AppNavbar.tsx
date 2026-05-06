import { Link, NavLink, useNavigate } from "react-router-dom";
import { Bell, ChevronDown, Globe2, LogOut, Settings, User } from "lucide-react";
import { useEffect, useRef, useState } from "react";

const links = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/plan",      label: "Plan Trip" },
  { to: "/chat",      label: "Chat" },
  { to: "/history",   label: "My Trips" },
  { to: "/profile",   label: "Profile" },
];

export function AppNavbar() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <header className="sticky top-0 z-40 backdrop-blur-xl bg-ink/70 border-b border-gold/15">
      <div className="container-luxe flex h-16 items-center justify-between">
        <Link to="/dashboard" className="flex items-center gap-2 group">
          <Globe2 className="h-5 w-5 text-gold transition-transform group-hover:rotate-12" />
          <span className="font-display italic text-xl">Travelmate</span>
        </Link>

        <nav className="flex items-center gap-1 overflow-x-auto">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              className={({ isActive }) =>
                `relative px-4 py-2 text-sm rounded-md transition-colors ${
                  isActive ? "text-gold" : "text-foreground/70 hover:text-foreground"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {l.label}
                  {isActive && (
                    <span className="absolute -bottom-0.5 left-1/2 -translate-x-1/2 h-px w-6 bg-gold" />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full border border-gold/20 bg-ink-soft">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-gold/60 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-gold" />
            </span>
            <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">8 agents online</span>
          </div>
          <button className="p-2 rounded-md hover:bg-ink-soft transition-colors" aria-label="Notifications">
            <Bell className="h-4 w-4 text-foreground/70" />
          </button>
          <div className="relative" ref={ref}>
            <button
              onClick={() => setOpen((o) => !o)}
              className="flex items-center gap-2 pl-1 pr-2 py-1 rounded-full border border-gold/20 hover:border-gold/40 transition-colors"
            >
              <div className="h-7 w-7 rounded-full bg-gradient-to-br from-gold to-gold-deep flex items-center justify-center text-[10px] font-medium text-ink">
                AT
              </div>
              <ChevronDown className="h-3 w-3 text-foreground/60" />
            </button>
            {open && (
              <div className="absolute right-0 mt-2 w-52 card-luxury p-1 animate-fade-in">
                <button onClick={() => { setOpen(false); navigate("/profile"); }} className="w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm hover:bg-ink-soft">
                  <User className="h-4 w-4 text-gold" /> Profile
                </button>
                <button className="w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm hover:bg-ink-soft">
                  <Settings className="h-4 w-4 text-gold" /> Settings
                </button>
                <div className="h-px bg-border my-1" />
                <button onClick={() => navigate("/")} className="w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm hover:bg-ink-soft text-destructive/90">
                  <LogOut className="h-4 w-4" /> Sign out
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
