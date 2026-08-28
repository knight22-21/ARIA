import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { api } from "@/lib/api";
import { Badge, EmptyState, PageHeader, Select, Skeleton } from "@/components/ui";
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

  return (
    <div className="space-y-6">
      <PageHeader
        title="Risk Events"
        subtitle="Detected revenue at risk across all recovery workflows."
        actions={
          <>
            <Select value={status} onChange={setStatus}>
              {STATUSES.map((o) => <option key={o} value={o}>{o ? o.replace(/_/g, " ") : "All statuses"}</option>)}
            </Select>
            <Select value={workflow} onChange={setWorkflow}>
              {WORKFLOWS.map((o) => <option key={o} value={o}>{o ? o.replace(/_/g, " ") : "All workflows"}</option>)}
            </Select>
          </>
        }
      />

      <div className="card-elevated overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/[0.06] text-left text-[11px] uppercase tracking-wider text-muted-foreground">
              <th className="px-5 py-3 font-medium">Workflow</th>
              <th className="px-5 py-3 font-medium">Amount</th>
              <th className="px-5 py-3 font-medium">Risk score</th>
              <th className="px-5 py-3 font-medium">Status</th>
              <th className="px-5 py-3 font-medium">Detected</th>
              <th className="w-8" />
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              Array.from({ length: 7 }).map((_, i) => (
                <tr key={i} className="border-b border-white/[0.04]">
                  <td className="px-5 py-4" colSpan={6}><Skeleton className="h-5" /></td>
                </tr>
              ))
            ) : !data?.length ? (
              <tr><td colSpan={6} className="p-6"><EmptyState title="No risk events" hint="Fire an event from the Command Center" /></td></tr>
            ) : (
              data.map((r) => (
                <tr
                  key={r.risk_event_id}
                  onClick={() => nav(`/risk/${r.risk_event_id}`)}
                  className="group cursor-pointer border-b border-white/[0.04] transition-colors last:border-0 hover:bg-white/[0.025]"
                >
                  <td className="px-5 py-3.5 font-medium capitalize">{r.workflow_type.replace(/_/g, " ")}</td>
                  <td className="px-5 py-3.5 tabular-nums">{formatINR(r.amount_at_risk_paise)}</td>
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-2.5">
                      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-white/[0.06]">
                        <div
                          className={cn("h-full rounded-full", r.risk_score > 0.7 ? "bg-danger" : r.risk_score > 0.5 ? "bg-warning" : "bg-info")}
                          style={{ width: `${r.risk_score * 100}%` }}
                        />
                      </div>
                      <span className="text-xs tabular-nums text-muted-foreground">{r.risk_score.toFixed(2)}</span>
                    </div>
                  </td>
                  <td className="px-5 py-3.5"><Badge label={r.status} tone={r.status} /></td>
                  <td className="px-5 py-3.5 text-xs text-muted-foreground">{new Date(r.detected_at).toLocaleString()}</td>
                  <td className="pr-4 text-muted-foreground/40">
                    <ChevronRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:text-foreground" />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
