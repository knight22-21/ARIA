import { useEffect, useRef, useState, type ElementType } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, Percent, Wallet } from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardTitle, Skeleton } from "@/components/ui";
import { Injector } from "@/components/Injector";
import { LiveFeed } from "@/components/LiveFeed";

function useCountUp(target: number, ms = 900) {
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

function Kpi({
  title,
  value,
  suffix,
  prefix,
  icon: Icon,
  tone,
  delay,
}: {
  title: string;
  value: number;
  suffix?: string;
  prefix?: string;
  icon: ElementType;
  tone: string;
  delay: number;
}) {
  const n = useCountUp(value);
  const display =
    prefix === "₹"
      ? `₹${Math.round(n).toLocaleString("en-IN")}`
      : `${prefix ?? ""}${n.toFixed(suffix === "%" ? 1 : 0)}${suffix ?? ""}`;
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
    >
      <Card>
        <div className="flex items-start justify-between">
          <CardTitle>{title}</CardTitle>
          <Icon className={`h-4 w-4 ${tone}`} />
        </div>
        <div className={`mt-3 text-3xl font-bold tracking-tight ${tone}`}>{display}</div>
      </Card>
    </motion.div>
  );
}

export default function CommandCenter() {
  const pnl = useQuery({ queryKey: ["pnl"], queryFn: api.pnl, refetchInterval: 4000 });
  const summary = useQuery({ queryKey: ["summary"], queryFn: api.summary, refetchInterval: 4000 });

  const escalated = summary.data?.by_status?.escalated?.count ?? 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Command Center</h1>
        <p className="text-sm text-muted-foreground">
          Every rupee that slips away leaves a trace. Detect · reason · recover · prove.
        </p>
      </div>

      {pnl.isLoading || summary.isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28" />)}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Kpi title="Revenue at Risk" value={pnl.data?.gross_revenue_at_risk ?? 0} prefix="₹" icon={Wallet} tone="text-foreground" delay={0} />
          <Kpi title="Recovered (attributed)" value={pnl.data?.recovered.attributed ?? 0} prefix="₹" icon={CheckCircle2} tone="text-primary" delay={0.08} />
          <Kpi title="Recovery Rate" value={pnl.data?.recovery_rate_pct ?? 0} suffix="%" icon={Percent} tone="text-accent" delay={0.16} />
          <Kpi title="Awaiting Review" value={escalated} icon={AlertTriangle} tone="text-warning" delay={0.24} />
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Injector />
        <div className="glass rounded-xl p-5">
          <CardTitle>Recovery Margin</CardTitle>
          <div className="mt-3 text-3xl font-bold text-primary">
            {(pnl.data?.recovery_margin_pct ?? 0).toFixed(1)}%
          </div>
          <div className="mt-2 grid grid-cols-2 gap-3 text-xs text-muted-foreground">
            <div>Net recovered<div className="text-sm font-semibold text-foreground">₹{(pnl.data?.net_recovered ?? 0).toLocaleString("en-IN")}</div></div>
            <div>Cost of recovery<div className="text-sm font-semibold text-foreground">₹{(pnl.data?.cost.total ?? 0).toLocaleString("en-IN")}</div></div>
            <div>Auto interventions<div className="text-sm font-semibold text-foreground">{pnl.data?.interventions.auto ?? 0}</div></div>
            <div>Escalated<div className="text-sm font-semibold text-foreground">{pnl.data?.interventions.escalated ?? 0}</div></div>
          </div>
        </div>
      </div>

      <LiveFeed />
    </div>
  );
}
