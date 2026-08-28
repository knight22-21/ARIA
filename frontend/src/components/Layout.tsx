import { NavLink, Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  Inbox,
  LayoutDashboard,
  LogOut,
  ScrollText,
  TrendingUp,
} from "lucide-react";
import { api } from "@/lib/api";
import { logout, DEMO_USER } from "@/lib/auth";
import { cn } from "@/lib/utils";

const NAV_GROUPS = [
  {
    label: "Monitor",
    items: [
      { to: "/", label: "Command Center", icon: LayoutDashboard, end: true },
      { to: "/risk", label: "Risk Events", icon: Activity },
    ],
  },
  {
    label: "Act",
    items: [
      { to: "/escalations", label: "Action Queue", icon: AlertTriangle },
      { to: "/outbox", label: "Outbox", icon: Inbox },
    ],
  },
  {
    label: "Measure",
    items: [
      { to: "/pnl", label: "Recovery P&L", icon: TrendingUp },
      { to: "/audit", label: "Audit Ledger", icon: ScrollText },
    ],
  },
];

function StatusPill() {
  const { isError, isLoading } = useQuery({
    queryKey: ["summary-ping"],
    queryFn: api.summary,
    refetchInterval: 5000,
  });
  const s = isLoading
    ? { t: "connecting", dot: "bg-muted-foreground", text: "text-muted-foreground" }
    : isError
      ? { t: "offline", dot: "bg-danger", text: "text-danger" }
      : { t: "online", dot: "bg-primary", text: "text-primary" };
  return (
    <div className="glass inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs">
      <span className="relative flex h-2 w-2">
        {!isError && !isLoading && (
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary/60" />
        )}
        <span className={cn("relative inline-flex h-2 w-2 rounded-full", s.dot)} />
      </span>
      <span className={s.text}>API {s.t}</span>
    </div>
  );
}

export default function Layout() {
  return (
    <div className="min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-20 flex w-[240px] flex-col border-r border-white/[0.06] bg-surface/60 backdrop-blur-2xl">
        <div className="flex items-center gap-3 px-5 py-6">
          <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent text-lg font-bold text-background shadow-[0_4px_16px_-4px_hsl(258_90%_60%/0.6)]">
            A
          </div>
          <div>
            <div className="text-[15px] font-semibold leading-tight">ARIA</div>
            <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
              Revenue Intelligence
            </div>
          </div>
        </div>

        <nav className="mt-2 flex-1 space-y-6 px-3">
          {NAV_GROUPS.map((group) => (
            <div key={group.label}>
              <div className="px-3 pb-2 text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground/50">
                {group.label}
              </div>
              <div className="space-y-0.5">
                {group.items.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) =>
                      cn(
                        "group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-all duration-200",
                        isActive
                          ? "bg-white/[0.05] text-foreground"
                          : "text-muted-foreground hover:bg-white/[0.03] hover:text-foreground",
                      )
                    }
                  >
                    {({ isActive }) => (
                      <>
                        {isActive && (
                          <span className="absolute inset-y-1.5 left-0 w-0.5 rounded-full bg-gradient-to-b from-primary to-accent" />
                        )}
                        <item.icon
                          className={cn(
                            "h-4 w-4 transition-colors",
                            isActive ? "text-accent" : "text-muted-foreground group-hover:text-foreground",
                          )}
                        />
                        {item.label}
                      </>
                    )}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>

        <div className="space-y-3 border-t border-white/[0.06] p-4">
          <StatusPill />
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-white/[0.06] text-[11px] font-semibold uppercase text-muted-foreground">
                {DEMO_USER.slice(0, 2)}
              </div>
              <span className="text-xs text-muted-foreground">{DEMO_USER}</span>
            </div>
            <button
              onClick={() => {
                logout();
                window.location.reload();
              }}
              title="Sign out"
              className="ring-focus rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-white/[0.05] hover:text-danger"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
          <div className="text-[10px] leading-relaxed text-muted-foreground/50">
            Razorpay AI Buildathon · Track 03
          </div>
        </div>
      </aside>

      <main className="ml-[240px] min-h-screen px-10 py-8">
        <div className="mx-auto max-w-[1400px]">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
