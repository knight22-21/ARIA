import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Activity, Brain, ShieldCheck, TrendingUp, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

interface Health {
  status: string;
  service: string;
  version: string;
}

async function fetchHealth(): Promise<Health> {
  const r = await fetch("/api/health");
  if (!r.ok) throw new Error("backend unreachable");
  return r.json();
}

function StatusPill() {
  const { data, isError, isLoading } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 5000,
  });

  const state = isLoading
    ? { label: "connecting…", tone: "text-muted-foreground", dot: "bg-muted-foreground" }
    : isError
      ? { label: "backend offline", tone: "text-danger", dot: "bg-danger" }
      : { label: `API v${data?.version} · online`, tone: "text-primary", dot: "bg-primary" };

  return (
    <div className="glass inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs">
      <span className={cn("h-2 w-2 rounded-full animate-pulse-glow", state.dot)} />
      <span className={state.tone}>{state.label}</span>
    </div>
  );
}

const PILLARS = [
  { icon: Activity, title: "Detect", body: "Multi-signal risk scoring across payment, checkout, subscription & receivables." },
  { icon: Brain, title: "Reason", body: "LLM causal diagnosis with a visible chain-of-thought — no black box." },
  { icon: Zap, title: "Execute", body: "Bounded, reversible action space with stopping rules & policy guards." },
  { icon: TrendingUp, title: "Measure", body: "Attributed recovery with a true per-run P&L, not vanity metrics." },
  { icon: ShieldCheck, title: "Prove", body: "Append-only, tamper-evident audit ledger for every decision." },
];

export default function App() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-border/60">
        <div className="container flex items-center justify-between py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent text-background font-bold">
              A
            </div>
            <div>
              <div className="font-semibold leading-tight">ARIA</div>
              <div className="text-xs text-muted-foreground">Autonomous Revenue Intelligence</div>
            </div>
          </div>
          <StatusPill />
        </div>
      </header>

      <main className="container py-16">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="max-w-3xl"
        >
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-border bg-secondary/40 px-3 py-1 text-xs text-muted-foreground">
            Razorpay AI Buildathon · Track 03 — Revenue Recovery
          </div>
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Every rupee that slips away <span className="text-gradient">leaves a trace.</span>
          </h1>
          <p className="mt-4 text-lg text-muted-foreground">
            ARIA reads that trace, reasons over it, and wins the money back — with proof.
          </p>
        </motion.div>

        <div className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {PILLARS.map((p, i) => (
            <motion.div
              key={p.title}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.1 + i * 0.08 }}
              className="glass rounded-xl p-5 transition-colors hover:border-primary/30"
            >
              <p.icon className="mb-3 h-5 w-5 text-primary" />
              <div className="font-semibold">{p.title}</div>
              <p className="mt-1 text-sm text-muted-foreground">{p.body}</p>
            </motion.div>
          ))}
        </div>

        <div className="mt-16 text-sm text-muted-foreground">
          Phase 0 scaffold · dashboard shell wired to the backend. Screens land in Phase 5.
        </div>
      </main>
    </div>
  );
}
