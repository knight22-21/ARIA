import { NavLink, Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  Inbox,
  LayoutDashboard,
  ScrollText,
  TrendingUp,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/", label: "Command Center", icon: LayoutDashboard, end: true },
  { to: "/risk", label: "Risk Events", icon: Activity },
  { to: "/escalations", label: "Action Queue", icon: AlertTriangle },
  { to: "/pnl", label: "Recovery P&L", icon: TrendingUp },
  { to: "/outbox", label: "Outbox", icon: Inbox },
  { to: "/audit", label: "Audit Ledger", icon: ScrollText },
];

function BackendStatus() {
  const { isError, isLoading } = useQuery({
    queryKey: ["summary-ping"],
    queryFn: api.summary,
    refetchInterval: 5000,
  });
  const s = isLoading
    ? { t: "connecting", c: "bg-muted-foreground text-muted-foreground" }
    : isError
      ? { t: "offline", c: "bg-danger text-danger" }
      : { t: "online", c: "bg-primary text-primary" };
  return (
    <div className="flex items-center gap-2 px-3 py-2 text-xs">
      <span className={cn("h-2 w-2 rounded-full animate-pulse-glow", s.c)} />
      <span className="text-muted-foreground">API {s.t}</span>
    </div>
  );
}

export default function Layout() {
  return (
    <div className="flex min-h-screen">
      <aside className="fixed inset-y-0 left-0 flex w-60 flex-col border-r border-border/60 bg-card/40 backdrop-blur-xl">
        <div className="flex items-center gap-3 px-5 py-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent font-bold text-background">
            A
          </div>
          <div>
            <div className="font-semibold leading-tight">ARIA</div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Revenue Intelligence
            </div>
          </div>
        </div>

        <nav className="mt-2 flex-1 space-y-1 px-3">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-secondary hover:text-foreground",
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-border/60">
          <BackendStatus />
          <div className="px-3 pb-3 text-[10px] text-muted-foreground/60">
            Razorpay AI Buildathon · Track 03
          </div>
        </div>
      </aside>

      <main className="ml-60 flex-1 px-8 py-6">
        <Outlet />
      </main>
    </div>
  );
}
