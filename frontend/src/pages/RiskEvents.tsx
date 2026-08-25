import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { Badge, EmptyState, Skeleton } from "@/components/ui";
import { formatINR, cn } from "@/lib/utils";

const STATUSES = ["", "detected", "in_progress", "recovered", "escalated", "suppressed", "unrecovered"];
const WORKFLOWS = ["", "payment_degradation", "subscription_failure", "b2b_receivable", "checkout_abandonment", "mandate_retry"];

export default function RiskEvents() {
  const nav = useNavigate();
  const [status, setStatus] = useState("");
  const [workflow, setWorkflow] = useState("");

  const q = new URLSearchParams();
  if (status) q.set("status", status);
  if (workflow) q.set("workflow", workflow);
  q.set("limit", "100");

  const { data, isLoading } = useQuery({
    queryKey: ["risk-events", status, workflow],
    queryFn: () => api.riskEvents(`?${q.toString()}`),
    refetchInterval: 3000,
  });

  const Select = ({ value, onChange, options, label }: { value: string; onChange: (v: string) => void; options: string[]; label: string }) => (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-lg border border-border bg-background/60 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring/50"
    >
      {options.map((o) => (
        <option key={o} value={o}>{o ? o.replace(/_/g, " ") : `All ${label}`}</option>
      ))}
    </select>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Risk Events</h1>
          <p className="text-sm text-muted-foreground">Detected revenue at risk across all workflows.</p>
        </div>
        <div className="flex gap-2">
          <Select value={status} onChange={setStatus} options={STATUSES} label="statuses" />
          <Select value={workflow} onChange={setWorkflow} options={WORKFLOWS} label="workflows" />
        </div>
      </div>

      <div className="glass overflow-hidden rounded-xl">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border/60 text-left text-xs uppercase tracking-wider text-muted-foreground">
              <th className="px-5 py-3 font-medium">Workflow</th>
              <th className="px-5 py-3 font-medium">Amount</th>
              <th className="px-5 py-3 font-medium">Risk</th>
              <th className="px-5 py-3 font-medium">Status</th>
              <th className="px-5 py-3 font-medium">Detected</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <tr key={i} className="border-b border-border/40">
                  <td className="px-5 py-4" colSpan={5}><Skeleton className="h-5" /></td>
                </tr>
              ))
            ) : !data?.length ? (
              <tr><td colSpan={5} className="p-6"><EmptyState title="No risk events" hint="Fire an event from the Command Center" /></td></tr>
            ) : (
              data.map((r) => (
                <tr
                  key={r.risk_event_id}
                  onClick={() => nav(`/risk/${r.risk_event_id}`)}
                  className="cursor-pointer border-b border-border/40 transition-colors hover:bg-secondary/40"
                >
                  <td className="px-5 py-3 font-medium">{r.workflow_type.replace(/_/g, " ")}</td>
                  <td className="px-5 py-3 tabular-nums">{formatINR(r.amount_at_risk_paise)}</td>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-secondary">
                        <div
                          className={cn("h-full rounded-full", r.risk_score > 0.7 ? "bg-danger" : r.risk_score > 0.5 ? "bg-warning" : "bg-info")}
                          style={{ width: `${r.risk_score * 100}%` }}
                        />
                      </div>
                      <span className="text-xs tabular-nums text-muted-foreground">{r.risk_score.toFixed(2)}</span>
                    </div>
                  </td>
                  <td className="px-5 py-3"><Badge label={r.status} tone={r.status} /></td>
                  <td className="px-5 py-3 text-xs text-muted-foreground">{new Date(r.detected_at).toLocaleString()}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
