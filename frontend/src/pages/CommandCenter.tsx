import { useEffect, useRef, useState, type ElementType } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, Percent, Wallet } from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardTitle, PageHeader, Skeleton } from "@/components/ui";
import { Injector } from "@/components/Injector";
import { LiveFeed } from "@/components/LiveFeed";

function useCountUp(target: number, ms = 1000) {
  const [val, setVal] = useState(0);
  const ref = useRef(0);
  useEffect(() => {
    const start = ref.current;
    const t0 = performance.now();
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.min(1, (t - t0) / ms);
      const eased = 1 - Math.pow(1 - p, 3);
      setVal(start + (target - start) * eased);
      if (p < 1) raf = requestAnimationFrame(tick);
      else ref.current = target;
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, ms]);
  return val;
}

const TINT: Record<string, string> = {
  neutral: "bg-white/[0.04] text-foreground",
  primary: "bg-primary/10 text-primary",
  accent: "bg-accent/10 text-accent",
  warning: "bg-warning/10 text-warning",
};

function Kpi({
  title,
  value,
  suffix,
  prefix,
  icon: Icon,
  tint,
  sub,
  delay,
}: {
  title: string;
  value: number;
  suffix?: string;
  prefix?: string;
  icon: ElementType;
  tint: keyof typeof TINT;
  sub?: string;
  delay: number;
}) {
  const n = useCountUp(value);
  const display =
    prefix === "₹"
      ? `₹${Math.round(n).toLocaleString("en-IN")}`
      : `${prefix ?? ""}${n.toFixed(suffix === "%" ? 1 : 0)}${suffix ?? ""}`;
  const numTone =
    tint === "primary" ? "text-primary" : tint === "accent" ? "text-accent" : tint === "warning" ? "text-warning" : "text-foreground";
  return (
    <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay, duration: 0.4 }}>
      <Card hover>
        <div className="flex items-center justify-between">
          <CardTitle>{title}</CardTitle>
          <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${TINT[tint]}`}>
            <Icon className="h-4 w-4" />
          </div>
        </div>
        <div className={`mt-3 text-[28px] font-bold leading-none tracking-tight tabular-nums ${numTone}`}>
          {display}
        </div>
        {sub && <div className="mt-2 text-xs text-muted-foreground">{sub}</div>}
      </Card>
    </motion.div>
  );
}

export default function CommandCenter() {
  const pnl = useQuery({ queryKey: ["pnl"], queryFn: api.pnl, refetchInterval: 4000 });
  const summary = useQuery({ queryKey: ["summary"], queryFn: api.summary, refetchInterval: 4000 });

  const bs = summary.data?.by_status ?? {};
  const escalated = bs.escalated?.count ?? 0;
  const recovered = bs.recovered?.count ?? 0;
  const loading = pnl.isLoading || summary.isLoading;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Command Center"
        subtitle="Every rupee that slips away leaves a trace. Detect · reason · recover · prove."
      />

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-32 rounded-2xl" />)}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Kpi title="Revenue at Risk" value={pnl.data?.gross_revenue_at_risk ?? 0} prefix="₹" icon={Wallet} tint="neutral" sub={`${summary.data?.total_events ?? 0} risk events`} delay={0} />
          <Kpi title="Recovered" value={pnl.data?.recovered.attributed ?? 0} prefix="₹" icon={CheckCircle2} tint="primary" sub={`${recovered} cases · attributed`} delay={0.08} />
          <Kpi title="Recovery Rate" value={pnl.data?.recovery_rate_pct ?? 0} suffix="%" icon={Percent} tint="accent" sub={`${pnl.data?.recovery_margin_pct ?? 0}% margin`} delay={0.16} />
          <Kpi title="Awaiting Review" value={escalated} icon={AlertTriangle} tint="warning" sub="in the action queue" delay={0.24} />
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <Injector />
        </div>
        <Card className="lg:col-span-2">
          <CardTitle>Recovery Economics</CardTitle>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-primary tabular-nums">
              {(pnl.data?.recovery_margin_pct ?? 0).toFixed(1)}%
            </span>
            <span className="text-xs text-muted-foreground">net margin</span>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-xs">
            {[
              ["Net recovered", `₹${(pnl.data?.net_recovered ?? 0).toLocaleString("en-IN")}`],
              ["Cost of recovery", `₹${(pnl.data?.cost.total ?? 0).toLocaleString("en-IN")}`],
              ["Auto interventions", `${pnl.data?.interventions.auto ?? 0}`],
              ["Escalated", `${pnl.data?.interventions.escalated ?? 0}`],
            ].map(([k, v]) => (
              <div key={k}>
                <div className="text-muted-foreground">{k}</div>
                <div className="mt-0.5 text-sm font-semibold tabular-nums text-foreground">{v}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <LiveFeed />
    </div>
  );
}
